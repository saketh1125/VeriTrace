"""Run lifecycle: validates input, drives face/discovery/matching with live
events, attests evidence, and verifies the chain commitment independently.

The service reuses VerificationOrchestrator's candidate loop through an event
sink so matching and evidence rules live in exactly one place.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

import numpy as np

from app.discovery.models import DiscoveryMethod, DiscoveryQuery, Platform
from app.extraction.media_fetcher import fetch_bytes
from app.face.service import FaceEmbedding
from app.matching.image import perceptual_similarity
from app.verification.orchestrator import (
    AttestationService,
    EventSink,
    FaceProcessor,
    VerificationOrchestrator,
)
from app.verification.verifier import verify_evidence_record

from .models import (
    BlockchainView,
    CandidateView,
    EvidenceView,
    PipelineStep,
    RunRecord,
    RunResult,
    RunStatus,
    new_run_id,
)
from .store import RunStore

FaceFactory = Callable[[], FaceProcessor]
BlockchainFactory = Callable[[], AttestationService]
MediaFetcher = Callable[[str], Any]
ImageSimilarity = Callable[[bytes, bytes], float]
Clock = Callable[[], datetime]

PLATFORM_HOSTS: dict[str, Platform] = {
    "instagram.com": Platform.INSTAGRAM,
    "linkedin.com": Platform.LINKEDIN,
    "facebook.com": Platform.FACEBOOK,
    "fb.com": Platform.FACEBOOK,
    "reddit.com": Platform.REDDIT,
}

MAX_FACE_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

PREFLIGHT_MESSAGES = {
    "NO_FACE_FOUND": "No usable face detected. Upload a clear, front-facing photo.",
    "MULTIPLE_FACES": (
        "VeriTrace requires one usable face in the input image. "
        "Retake or upload a single-person image."
    ),
    "FACE_QUALITY_LOW": "The face in this image is too small or unclear. Use a larger, well-lit photo.",
    "INPUT_INVALID": "That file is not a readable JPG, PNG, or WEBP image.",
}


class RunRequestError(ValueError):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


class _RunFailure(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


def detect_platform(target: str) -> Platform | None:
    host = (urlparse(target).hostname or "").lower()
    for suffix, platform in PLATFORM_HOSTS.items():
        if host == suffix or host.endswith(f".{suffix}"):
            return platform
    return None


def normalize_mode(mode: str) -> DiscoveryMethod:
    if mode.strip().lower() in {"post", "direct-post", "direct_post"}:
        return DiscoveryMethod.DIRECT_POST
    return DiscoveryMethod.PROFILE


def build_discovery_query(
    platform: Platform | None, mode: str, target: str, max_posts: int
) -> DiscoveryQuery:
    method = normalize_mode(mode)
    cleaned = target.strip()
    if not cleaned:
        raise RunRequestError("TARGET_REQUIRED", "A username, profile URL, or post URL is required.")
    detected = detect_platform(cleaned) if "://" in cleaned else None
    resolved = platform or detected or Platform.INSTAGRAM
    bounded = max(1, min(max_posts, 50))
    if method == DiscoveryMethod.DIRECT_POST:
        if not cleaned.startswith(("http://", "https://")):
            raise RunRequestError("POST_URL_REQUIRED", "Post mode needs a direct public post URL.")
        return DiscoveryQuery(
            platform=resolved, post_url=cleaned, max_posts=bounded, method=method  # type: ignore[arg-type]
        )
    if cleaned.startswith(("http://", "https://")):
        return DiscoveryQuery(
            platform=resolved, profile_url=cleaned, max_posts=bounded, method=method  # type: ignore[arg-type]
        )
    return DiscoveryQuery(
        platform=resolved, username=cleaned.lstrip("@"), max_posts=bounded, method=method
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _candidate_id(index: int) -> str:
    return f"cand_{index + 1:02d}"


class _RunEventSink:
    """Forwards orchestrator hooks to the store and maintains candidate views."""

    REJECT_STATUS = {
        "NO_FACE_FOUND": ("NO_FACE", "NO_FACE_IN_MEDIA"),
        "FACE_THRESHOLD_NOT_MET": ("LOW_SCORE", "FACE_MATCH_LOW"),
        "UNSUPPORTED_MEDIA_TYPE": ("SKIPPED", "UNSUPPORTED_MEDIA_TYPE"),
    }

    def __init__(self, store: RunStore, run_id: str) -> None:
        self._store = store
        self._run_id = run_id

    def emit(self, event: str, data: dict[str, Any]) -> None:
        record = self._store.get(self._run_id)
        candidate_id = self._candidate_id_for(record, data)
        self._apply_to_candidate(record, event, data, candidate_id)
        self._store.append_event(self._run_id, event, data, candidate_id=candidate_id)
        if event == "CANDIDATE_MATCH_RESULT":
            self._store.append_event(
                self._run_id,
                "FACE_MATCH",
                {
                    "score": data.get("face_similarity"),
                    "threshold": data.get("face_threshold"),
                    "decision": data.get("decision"),
                    "reason": data.get("reason"),
                },
                candidate_id=candidate_id,
            )

    def _candidate_id_for(self, record: RunRecord | None, data: dict[str, Any]) -> str | None:
        if record is None or "media_url" not in data:
            return None
        for candidate in record.candidates:
            if candidate.media_url == data["media_url"] and candidate.post_url == data.get(
                "post_url", candidate.post_url
            ):
                return candidate.candidate_id
        return None

    def _apply_to_candidate(
        self,
        record: RunRecord | None,
        event: str,
        data: dict[str, Any],
        candidate_id: str | None,
    ) -> None:
        if record is None or candidate_id is None:
            return
        candidate = next(
            (item for item in record.candidates if item.candidate_id == candidate_id), None
        )
        if candidate is None:
            return
        if event == "MEDIA_FETCH_STARTED":
            candidate.status = "PROCESSING"
            self._store.update(self._run_id, pipeline_step=PipelineStep.FETCHING_MEDIA)
        elif event == "MEDIA_FETCH_COMPLETED" and data.get("ok") is False:
            candidate.status = "MEDIA_FAILED"
            candidate.reason = f"MEDIA_FETCH_FAILED:{data.get('reason', 'UNKNOWN')}"
            self._store.update(self._run_id, pipeline_step=PipelineStep.FETCHING_MEDIA)
        elif event == "CANDIDATE_MATCH_STARTED":
            candidate.status = "PROCESSING"
            self._store.update(self._run_id, pipeline_step=PipelineStep.MATCHING)
        elif event == "CANDIDATE_MATCH_RESULT":
            self._apply_match_result(candidate, data)
        elif event in {"EVIDENCE_CREATED", "HASH_COMPUTED"}:
            self._store.update(self._run_id, pipeline_step=PipelineStep.BUILDING_EVIDENCE)

    def _apply_match_result(self, candidate: CandidateView, data: dict[str, Any]) -> None:
        if data.get("decision") == "accept":
            candidate.status = "ACCEPTED"
            candidate.reason = "VERIFIED_MATCH"
            candidate.face_similarity = data.get("face_similarity")
            candidate.image_similarity = data.get("image_similarity")
        else:
            reason = str(data.get("reason", "UNKNOWN"))
            status, reason_code = self.REJECT_STATUS.get(reason, ("MEDIA_FAILED", "MEDIA_FETCH_FAILED"))
            if reason not in self.REJECT_STATUS:
                reason_code = f"MEDIA_FETCH_FAILED:{reason}"
            candidate.status = status
            candidate.reason = reason_code
            candidate.face_similarity = data.get("face_similarity")
        record = self._store.get(self._run_id)
        processed = (
            sum(1 for item in record.candidates if item.status not in {"DISCOVERED", "PROCESSING"})
            if record
            else 0
        )
        self._store.update(
            self._run_id, pipeline_step=PipelineStep.MATCHING, processed_count=processed
        )


class RunService:
    def __init__(
        self,
        store: RunStore,
        providers: dict[Platform, Any],
        face_factory: FaceFactory | None = None,
        blockchain_factory: BlockchainFactory | None = None,
        registry_address: str = "",
        media_fetcher: MediaFetcher = fetch_bytes,
        image_similarity: ImageSimilarity = perceptual_similarity,
        face_threshold: float = 0.45,
        clock: Clock = _utcnow,
    ) -> None:
        self.store = store
        self.providers = providers
        self._face_factory = face_factory
        self._face: FaceProcessor | None = None
        self._blockchain_factory = blockchain_factory
        self.registry_address = registry_address
        self.media_fetcher = media_fetcher
        self.image_similarity = image_similarity
        self.face_threshold = face_threshold
        self.clock = clock

    @property
    def face_loaded(self) -> bool:
        return self._face is not None

    def face_service(self) -> FaceProcessor:
        if self._face is None:
            if self._face_factory is None:
                raise _RunFailure(
                    "FACE_MODEL_UNAVAILABLE", "Face model is not configured on this host."
                )
            try:
                self._face = self._face_factory()
            except _RunFailure:
                raise
            except Exception as exc:
                raise _RunFailure(
                    "INSIGHTFACE_INITIALIZATION_FAILED",
                    "Face model failed to initialize.",
                ) from exc
        return self._face

    def create_run(
        self,
        face_bytes: bytes,
        platform: Platform | None,
        mode: str,
        target: str,
        consent_version: str,
        consent_accepted: bool,
        max_posts: int,
        attest: bool,
    ) -> tuple[RunRecord, DiscoveryQuery]:
        if not consent_accepted:
            raise RunRequestError("CONSENT_REQUIRED", "Explicit consent is required.")
        if consent_version != "1.0":
            raise RunRequestError(
                "UNSUPPORTED_CONSENT_VERSION", "Only consent version 1.0 is supported."
            )
        if not face_bytes:
            raise RunRequestError("INPUT_INVALID", PREFLIGHT_MESSAGES["INPUT_INVALID"])
        if len(face_bytes) > MAX_FACE_IMAGE_BYTES:
            raise RunRequestError("INPUT_INVALID", "Face image exceeds the 10 MB limit.")
        query = build_discovery_query(platform, mode, target, max_posts)
        now = self.clock()
        record = RunRecord(
            run_id=new_run_id(now),
            status=RunStatus.RUNNING,
            pipeline_step=PipelineStep.VALIDATING_INPUT,
            platform=query.platform.value,
            method=query.method.value,
            target=target.strip(),
            max_posts=query.max_posts,
            attest=attest,
            consent_version=consent_version,
            created_at=now,
            updated_at=now,
        )
        self.store.create(record)
        self.store.append_event(
            record.run_id,
            "RUN_STARTED",
            {
                "platform": record.platform,
                "method": record.method,
                "max_posts": record.max_posts,
                "attest": attest,
            },
        )
        return record, query

    async def execute_run(
        self,
        run_id: str,
        face_bytes: bytes,
        query: DiscoveryQuery,
        consent_version: str,
        attest: bool,
    ) -> RunRecord:
        started = self.clock()
        try:
            self.store.update(run_id, pipeline_step=PipelineStep.VALIDATING_INPUT)
            self.store.append_event(run_id, "CONSENT_ACCEPTED", {})
            embedding = await self._process_face(run_id, face_bytes)
            posts = await self._discover(run_id, query)
            self._register_candidates(run_id, posts)
            match = await self._match(run_id, face_bytes, embedding, posts, query, consent_version)
            blockchain = await self._attest_and_verify(run_id, match, attest)
            return self._complete(run_id, match, blockchain, started)
        except _RunFailure as failure:
            return self._fail(run_id, failure.code, str(failure), started)
        except Exception as exc:
            return self._fail(run_id, "RUN_FAILED", type(exc).__name__, started)

    async def _process_face(self, run_id: str, face_bytes: bytes) -> FaceEmbedding:
        self.store.update(run_id, pipeline_step=PipelineStep.PROCESSING_FACE)
        self.store.append_event(run_id, "FACE_DETECTION_STARTED", {})
        try:
            embedding = await asyncio.to_thread(self.face_service().embed_image, face_bytes)
        except _RunFailure:
            raise
        except ValueError as exc:
            raise _RunFailure(*self._face_error(str(exc))) from exc
        self.store.append_event(
            run_id, "FACE_DETECTED", {"det_score": round(embedding.det_score, 4)}
        )
        self.store.append_event(
            run_id, "EMBEDDING_CREATED", {"dimensions": int(np.asarray(embedding.vector).size)}
        )
        return embedding

    def _face_error(self, code: str) -> tuple[str, str]:
        if "MULTIPLE_FACES" in code:
            return "MULTIPLE_FACES", PREFLIGHT_MESSAGES["MULTIPLE_FACES"]
        if "NO_FACE_FOUND" in code:
            return "NO_FACE_FOUND", PREFLIGHT_MESSAGES["NO_FACE_FOUND"]
        if "FACE_QUALITY_TOO_LOW" in code:
            return "FACE_QUALITY_LOW", PREFLIGHT_MESSAGES["FACE_QUALITY_LOW"]
        return "INPUT_INVALID", PREFLIGHT_MESSAGES["INPUT_INVALID"]

    async def _discover(self, run_id: str, query: DiscoveryQuery) -> list[Any]:
        self.store.update(run_id, pipeline_step=PipelineStep.DISCOVERING)
        self.store.append_event(
            run_id,
            "DISCOVERY_STARTED",
            {"platform": query.platform.value, "method": query.method.value},
        )
        provider = self.providers.get(query.platform)
        if provider is None:
            raise _RunFailure("DISCOVERY_PROVIDER_ERROR", "Platform is not supported.")
        try:
            posts = await asyncio.to_thread(provider.discover, query)
        except Exception as exc:
            raise _RunFailure("DISCOVERY_PROVIDER_ERROR", type(exc).__name__) from exc
        usable = [post for post in posts if post.post_url and post.media]
        self.store.append_event(
            run_id, "DISCOVERY_PROGRESS", {"discovered": len(posts), "usable": len(usable)}
        )
        self.store.append_event(
            run_id,
            "DISCOVERY_COMPLETED",
            {
                "candidate_posts": len(posts),
                "media_assets": sum(len(post.media) for post in posts),
            },
        )
        if not usable:
            raise _RunFailure(
                "NO_CANDIDATES", "Discovery completed with zero usable candidates."
            )
        return posts

    def _register_candidates(self, run_id: str, posts: list[Any]) -> None:
        candidates: list[CandidateView] = []
        for index, (post, media) in enumerate(VerificationOrchestrator._rank_posts(posts)):
            candidates.append(
                CandidateView(
                    candidate_id=_candidate_id(index),
                    post_url=str(post.post_url),
                    platform=post.platform.value,
                    author=post.author_username or post.author_name,
                    published_at=post.published_at,
                    media_url=str(media.url),
                    media_type=media.media_type,
                )
            )
        self.store.update(
            run_id, candidates=candidates, candidate_count=len(candidates), processed_count=0
        )

    async def _match(
        self,
        run_id: str,
        face_bytes: bytes,
        embedding: FaceEmbedding,
        posts: list[Any],
        query: DiscoveryQuery,
        consent_version: str,
    ) -> Any:
        self.store.update(run_id, pipeline_step=PipelineStep.FETCHING_MEDIA)
        orchestrator = VerificationOrchestrator(
            self.face_service(),
            self.face_threshold,
            media_fetcher=self.media_fetcher,
            image_similarity=self.image_similarity,
            clock=self.clock,
            events=_RunEventSink(self.store, run_id),
        )
        try:
            return await orchestrator.run(
                face_bytes,
                input_face=embedding,
                posts=posts,
                discovery_method=query.method.value,
                consent_version=consent_version,
                consent_timestamp=self.clock(),
                attest=False,
            )
        except RuntimeError as exc:
            if "NO_VERIFIED_CANDIDATE" in str(exc):
                raise _RunFailure(
                    "NO_VERIFIED_CANDIDATE",
                    "Search completed. No candidate passed face verification.",
                ) from exc
            raise _RunFailure("RUN_FAILED", str(exc)) from exc

    async def _attest_and_verify(self, run_id: str, match: Any, attest: bool) -> BlockchainView:
        digest = match.evidence.evidence_sha256 or ""
        blockchain = BlockchainView(evidence_hash=digest, registry=self.registry_address or None)
        if not attest:
            return blockchain
        self.store.update(run_id, pipeline_step=PipelineStep.ATTESTING)
        self.store.append_event(run_id, "BLOCKCHAIN_SUBMISSION_STARTED", {"evidence_sha256": digest})
        registry = self._blockchain_or_none(run_id)
        if registry is None:
            blockchain.status = "FAILED"
            self.store.append_event(
                run_id,
                "BLOCKCHAIN_SUBMISSION_FAILED",
                {"reason": "BLOCKCHAIN_NOT_CONFIGURED"},
            )
            return blockchain
        try:
            tx_hash = await asyncio.to_thread(registry.attest, digest)
        except Exception as exc:
            blockchain.status = "FAILED"
            self.store.append_event(
                run_id, "BLOCKCHAIN_SUBMISSION_FAILED", {"reason": type(exc).__name__}
            )
            return blockchain
        blockchain.status = "SUBMITTED"
        blockchain.tx_hash = tx_hash
        self.store.append_event(run_id, "BLOCKCHAIN_SUBMITTED", {"tx_hash": tx_hash})
        self.store.update(run_id, pipeline_step=PipelineStep.VERIFYING)
        try:
            integrity = await asyncio.to_thread(
                verify_evidence_record, match.evidence, registry  # type: ignore[arg-type]
            )
        except Exception as exc:
            blockchain.integrity = "UNKNOWN"
            self.store.append_event(
                run_id,
                "BLOCKCHAIN_SUBMISSION_FAILED",
                {"stage": "verification", "reason": type(exc).__name__},
            )
            return blockchain
        blockchain.integrity = integrity
        if integrity == "VERIFIED":
            blockchain.status = "CONFIRMED"
        self.store.append_event(
            run_id, "BLOCKCHAIN_VERIFIED", {"integrity": integrity, "tx_hash": tx_hash}
        )
        return blockchain

    def _blockchain_or_none(self, run_id: str) -> Any | None:
        del run_id
        if self._blockchain_factory is None:
            return None
        try:
            return self._blockchain_factory()
        except Exception:
            return None

    def _complete(
        self, run_id: str, match: Any, blockchain: BlockchainView, started: datetime
    ) -> RunRecord:
        evidence = EvidenceView(
            post_url=str(match.post.post_url),
            platform=match.post.platform.value,
            media_url=match.media_url,
            media_sha256=match.evidence.media.sha256,
            evidence_sha256=match.evidence.evidence_sha256,
            face_similarity=match.face_similarity,
            image_similarity=match.image_similarity,
            face_threshold=self.face_threshold,
        )
        duration_ms = int((self.clock() - started).total_seconds() * 1000)
        record = self.store.get(run_id)
        processed = (
            sum(1 for item in record.candidates if item.status not in {"DISCOVERED", "PROCESSING"})
            if record
            else 0
        )
        self.store.update(
            run_id,
            status=RunStatus.COMPLETED,
            pipeline_step=PipelineStep.COMPLETED,
            processed_count=processed,
            result=RunResult(outcome="VERIFIED", evidence=evidence, blockchain=blockchain),
            duration_ms=duration_ms,
        )
        self.store.append_event(
            run_id,
            "RUN_COMPLETED",
            {
                "outcome": "VERIFIED",
                "evidence_sha256": evidence.evidence_sha256,
                "face_similarity": evidence.face_similarity,
                "blockchain_status": blockchain.status,
                "integrity": blockchain.integrity,
            },
        )
        final = self.store.get(run_id)
        assert final is not None
        return final

    def _fail(self, run_id: str, code: str, message: str, started: datetime) -> RunRecord:
        duration_ms = int((self.clock() - started).total_seconds() * 1000)
        self.store.update(
            run_id,
            status=RunStatus.FAILED,
            pipeline_step=PipelineStep.FAILED,
            error_code=code,
            error_message=message,
            duration_ms=duration_ms,
        )
        self.store.append_event(run_id, "RUN_FAILED", {"code": code, "message": message})
        final = self.store.get(run_id)
        assert final is not None
        return final

    async def preflight_face(self, face_bytes: bytes) -> dict[str, Any]:
        if not face_bytes or len(face_bytes) > MAX_FACE_IMAGE_BYTES:
            return {"ok": False, "error_code": "INPUT_INVALID", "message": PREFLIGHT_MESSAGES["INPUT_INVALID"]}
        try:
            embedding = await asyncio.to_thread(self.face_service().embed_image, face_bytes)
        except _RunFailure:
            return {
                "ok": False,
                "error_code": "FACE_MODEL_UNAVAILABLE",
                "message": "Face model is not available on this host.",
            }
        except ValueError as exc:
            code, message = self._face_error(str(exc))
            faces_detected = 0 if code == "NO_FACE_FOUND" else (2 if code == "MULTIPLE_FACES" else 1)
            return {
                "ok": False,
                "error_code": code,
                "message": message,
                "faces_detected": faces_detected,
            }
        return {
            "ok": True,
            "faces_detected": 1,
            "det_score": round(embedding.det_score, 4),
        }

    async def wait_for_completion(self, run_id: str, timeout: float = 60.0) -> RunRecord | None:
        try:
            async with asyncio.timeout(timeout):
                while True:
                    record = self.store.get(run_id)
                    if record is None or record.status in {RunStatus.COMPLETED, RunStatus.FAILED}:
                        return record
                    await asyncio.sleep(0.05)
        except TimeoutError:
            return self.store.get(run_id)


def empty_sink() -> EventSink:
    class _Null:
        def emit(self, event: str, data: dict[str, Any]) -> None:
            del event, data

    return _Null()

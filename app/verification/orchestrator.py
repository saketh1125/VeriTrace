from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol

import numpy as np

from app.discovery.base import SocialContentProvider
from app.discovery.models import DiscoveryQuery, MediaAsset, SocialPost
from app.evidence.hashing import evidence_hash, sha256_bytes
from app.evidence.models import EvidenceMedia, EvidenceRecord, EvidenceSource, MatchingEvidence
from app.extraction.media_fetcher import fetch_bytes
from app.face.service import FaceEmbedding
from app.matching.image import perceptual_similarity
from app.matching.policy import decide


class FaceProcessor(Protocol):
    def embed_image(self, image_bytes: bytes) -> FaceEmbedding: ...

    def embeddings_in_image(self, image_bytes: bytes) -> list[np.ndarray]: ...

    @staticmethod
    def cosine_similarity(first: np.ndarray, second: np.ndarray) -> float: ...


class AttestationService(Protocol):
    def attest(self, evidence_hash_hex: str) -> str: ...


class EventSink(Protocol):
    """Observer for pipeline boundaries. Lets SSE streaming reuse the one
    candidate loop instead of duplicating matching/evidence logic."""

    def emit(self, event: str, data: dict[str, Any]) -> None: ...


MediaFetcher = Callable[[str], Awaitable[tuple[bytes, str]]]
ImageSimilarity = Callable[[bytes, bytes], float]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class CandidateFailure:
    media_url: str
    reason: str


@dataclass(frozen=True)
class VerifiedMatch:
    post: SocialPost
    media_url: str
    media_type: str
    image_similarity: float
    face_similarity: float
    evidence: EvidenceRecord
    attestation_tx_hash: str | None = None
    candidate_failures: tuple[CandidateFailure, ...] = field(default_factory=tuple)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VerificationOrchestrator:
    def __init__(
        self,
        face_service: FaceProcessor,
        face_threshold: float,
        discovery_provider: SocialContentProvider | None = None,
        blockchain_service: AttestationService | None = None,
        media_fetcher: MediaFetcher = fetch_bytes,
        image_similarity: ImageSimilarity = perceptual_similarity,
        clock: Clock = _utcnow,
        events: EventSink | None = None,
    ) -> None:
        self.face_service = face_service
        self.face_threshold = face_threshold
        self.discovery_provider = discovery_provider
        self.blockchain_service = blockchain_service
        self.media_fetcher = media_fetcher
        self.image_similarity = image_similarity
        self.clock = clock
        self.events = events

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self.events is not None:
            self.events.emit(event, data)

    async def run(
        self,
        input_image: bytes,
        input_face: FaceEmbedding | DiscoveryQuery | None = None,
        posts: list[SocialPost] | None = None,
        discovery_method: str | None = None,
        consent_version: str = "1.0",
        consent_timestamp: datetime | None = None,
        *,
        query: DiscoveryQuery | None = None,
        consent_accepted: bool | None = None,
        attest: bool = False,
    ) -> VerifiedMatch:
        if not input_image:
            raise ValueError("INPUT_IMAGE_REQUIRED")
        if consent_accepted is False:
            raise ValueError("CONSENT_REQUIRED")
        if isinstance(input_face, DiscoveryQuery):
            if query is not None:
                raise ValueError("DUPLICATE_DISCOVERY_QUERY")
            query = input_face
            input_face = None
        if query is not None:
            if self.discovery_provider is None:
                raise ValueError("DISCOVERY_PROVIDER_REQUIRED")
            self._emit(
                "DISCOVERY_STARTED",
                {"platform": query.platform.value, "method": query.method.value},
            )
            posts = self.discovery_provider.discover(query)
            discovery_method = query.method.value
            self._emit(
                "DISCOVERY_COMPLETED",
                {
                    "candidate_posts": len(posts),
                    "media_assets": sum(len(post.media) for post in posts),
                },
            )
        if posts is None:
            raise ValueError("DISCOVERY_POSTS_REQUIRED")
        if input_face is None:
            face = self.face_service.embed_image(input_image)
        else:
            face = input_face

        now = self.clock()
        consent_at = consent_timestamp or now
        failures: list[CandidateFailure] = []
        for index, (post, media) in enumerate(self._rank_posts(posts)):
            media_url = str(media.url)
            post_url = str(post.post_url)
            candidate_ref = {
                "post_url": post_url,
                "media_url": media_url,
                "index": index,
            }
            if media.media_type != "image":
                failures.append(CandidateFailure(media_url, "UNSUPPORTED_MEDIA_TYPE"))
                self._emit(
                    "CANDIDATE_MATCH_RESULT",
                    {
                        **candidate_ref,
                        "decision": "reject",
                        "reason": "UNSUPPORTED_MEDIA_TYPE",
                        "face_threshold": self.face_threshold,
                    },
                )
                continue
            self._emit("MEDIA_FETCH_STARTED", {**candidate_ref, "media_type": media.media_type})
            try:
                media_bytes, content_type = await self.media_fetcher(media_url)
            except Exception as exc:
                reason = type(exc).__name__
                failures.append(CandidateFailure(media_url, reason))
                self._emit("MEDIA_FETCH_COMPLETED", {**candidate_ref, "ok": False, "reason": reason})
                continue
            self._emit(
                "MEDIA_FETCH_COMPLETED",
                {**candidate_ref, "ok": True, "content_type": content_type},
            )
            self._emit("CANDIDATE_MATCH_STARTED", candidate_ref)
            try:
                embeddings = self.face_service.embeddings_in_image(media_bytes)
                if not embeddings:
                    failures.append(CandidateFailure(media_url, "NO_FACE_FOUND"))
                    self._emit(
                        "CANDIDATE_MATCH_RESULT",
                        {
                            **candidate_ref,
                            "decision": "reject",
                            "reason": "NO_FACE_FOUND",
                            "face_threshold": self.face_threshold,
                        },
                    )
                    continue
                face_similarity = max(
                    self.face_service.cosine_similarity(face.vector, candidate)
                    for candidate in embeddings
                )
                decision = decide(face_similarity, self.face_threshold)
                if not decision.verified:
                    failures.append(CandidateFailure(media_url, "FACE_THRESHOLD_NOT_MET"))
                    self._emit(
                        "CANDIDATE_MATCH_RESULT",
                        {
                            **candidate_ref,
                            "decision": "reject",
                            "reason": "FACE_THRESHOLD_NOT_MET",
                            "face_similarity": face_similarity,
                            "face_threshold": self.face_threshold,
                        },
                    )
                    continue
                image_similarity = self.image_similarity(input_image, media_bytes)
            except Exception as exc:
                reason = type(exc).__name__
                failures.append(CandidateFailure(media_url, reason))
                self._emit(
                    "CANDIDATE_MATCH_RESULT",
                    {**candidate_ref, "decision": "reject", "reason": reason},
                )
                continue
            self._emit(
                "CANDIDATE_MATCH_RESULT",
                {
                    **candidate_ref,
                    "decision": "accept",
                    "reason": "VERIFIED_MATCH",
                    "face_similarity": face_similarity,
                    "face_threshold": self.face_threshold,
                    "image_similarity": image_similarity,
                },
            )

            source = EvidenceSource(
                platform=post.platform.value,
                post_url=str(post.post_url),
                author_username=post.author_username,
                author_name=post.author_name,
                post_id=post.post_id,
                published_at=post.published_at,
            )
            record = EvidenceRecord(
                source=source,
                media=EvidenceMedia(
                    media_url=media_url,
                    sha256=sha256_bytes(media_bytes),
                    media_type=media.media_type,
                ),
                matching=MatchingEvidence(
                    image_similarity=image_similarity,
                    face_similarity=face_similarity,
                    image_threshold=0.0,
                    face_threshold=self.face_threshold,
                ),
                discovery_method=discovery_method or "profile",
                retrieved_at=now,
                consent_version=consent_version,
                consent_timestamp=consent_at,
                input_face_embedding_sha256=sha256_bytes(
                    np.asarray(face.vector, dtype=np.float32).tobytes()
                ),
            )
            digest = evidence_hash(record)
            record = record.model_copy(update={"evidence_sha256": digest})
            self._emit(
                "EVIDENCE_CREATED",
                {"post_url": str(post.post_url), "media_url": media_url},
            )
            self._emit("HASH_COMPUTED", {"evidence_sha256": digest})
            tx_hash: str | None = None
            if attest:
                if self.blockchain_service is None:
                    raise ValueError("BLOCKCHAIN_SERVICE_REQUIRED")
                self._emit("BLOCKCHAIN_SUBMISSION_STARTED", {"evidence_sha256": digest})
                tx_hash = self.blockchain_service.attest(digest)
                self._emit("BLOCKCHAIN_SUBMITTED", {"tx_hash": tx_hash})
                record = record.model_copy(update={"blockchain_evidence_hash": digest})
            return VerifiedMatch(
                post=post,
                media_url=media_url,
                media_type=media.media_type,
                image_similarity=image_similarity,
                face_similarity=face_similarity,
                evidence=record,
                attestation_tx_hash=tx_hash,
                candidate_failures=tuple(failures),
            )
        raise RuntimeError("NO_VERIFIED_CANDIDATE")

    @staticmethod
    def _rank_posts(posts: list[SocialPost]) -> list[tuple[SocialPost, MediaAsset]]:
        return [(post, media) for post in posts for media in post.media]

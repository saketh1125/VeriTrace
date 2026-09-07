from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.runs import get_run_service
from app.discovery.models import DiscoveryMethod, DiscoveryQuery, MediaAsset, Platform, SocialPost
from app.face.service import FaceEmbedding
from app.runs.models import REQUIRED_EVENTS
from app.runs.service import RunRequestError, RunService, build_discovery_query
from app.runs.store import RunStore

FIXED = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def make_post(url: str = "https://www.instagram.com/p/abc/") -> SocialPost:
    return SocialPost(
        platform=Platform.INSTAGRAM,
        post_url=url,  # type: ignore[arg-type]
        post_id="abc",
        author_username="example",
        media=[MediaAsset(url="https://cdn.example.test/m1.jpg")],  # type: ignore[arg-type]
    )


class FakeProvider:
    def __init__(self, posts: list[SocialPost] | None = None, error: Exception | None = None):
        self.posts = posts if posts is not None else [make_post()]
        self.error = error

    def discover(self, query: DiscoveryQuery) -> list[SocialPost]:
        if self.error is not None:
            raise self.error
        return self.posts


class FakeFace:
    def __init__(self, candidate_vectors: list[np.ndarray] | None = None, embed_error: Exception | None = None):
        self.candidate_vectors = candidate_vectors or [np.array([1.0, 0.0], dtype=np.float32)]
        self.embed_error = embed_error

    def embed_image(self, image_bytes: bytes) -> FaceEmbedding:
        if self.embed_error is not None:
            raise self.embed_error
        return FaceEmbedding(
            vector=np.array([1.0, 0.0], dtype=np.float32),
            bbox=(0.0, 0.0, 10.0, 10.0),
            det_score=0.99,
        )

    def embeddings_in_image(self, image_bytes: bytes) -> list[np.ndarray]:
        return self.candidate_vectors

    @staticmethod
    def cosine_similarity(first: np.ndarray, second: np.ndarray) -> float:
        first = np.asarray(first, dtype=np.float32).reshape(-1)
        second = np.asarray(second, dtype=np.float32).reshape(-1)
        denom = float(np.linalg.norm(first) * np.linalg.norm(second))
        return float(np.dot(first, second) / denom) if denom else 0.0


class FakeChain:
    def __init__(self, exists: bool = True, attest_error: Exception | None = None):
        self.exists = exists
        self.attest_error = attest_error
        self.attested: list[str] = []

    def attest(self, digest: str) -> str:
        if self.attest_error is not None:
            raise self.attest_error
        self.attested.append(digest)
        return "0xabc123"

    def verify(self, digest: str) -> dict:
        return {"exists": self.exists, "timestamp": 1, "submitter": "0xattester"}


async def fake_fetch(url: str) -> tuple[bytes, str]:
    return b"candidate-image", "image/jpeg"


def make_service(
    face: FakeFace | None = None,
    provider: FakeProvider | None = None,
    chain: FakeChain | None = None,
) -> tuple[RunService, FakeChain]:
    face = face or FakeFace()
    chain = chain if chain is not None else FakeChain()
    service = RunService(
        RunStore(),
        {Platform.INSTAGRAM: provider or FakeProvider()},
        face_factory=lambda: face,  # type: ignore[return-value]
        blockchain_factory=lambda: chain,  # type: ignore[return-value]
        registry_address="0xregistry",
        media_fetcher=fake_fetch,  # type: ignore[arg-type]
        image_similarity=lambda first, second: 0.74,
        face_threshold=0.45,
        clock=lambda: FIXED,
    )
    return service, chain


def make_query() -> DiscoveryQuery:
    return DiscoveryQuery(
        platform=Platform.INSTAGRAM,
        username="example",
        max_posts=5,
        method=DiscoveryMethod.PROFILE,
    )


def event_names(service: RunService, run_id: str) -> list[str]:
    record = service.store.get(run_id)
    assert record is not None
    return [entry.event for entry in record.events]


def test_build_discovery_query_profile_username_and_post_url() -> None:
    query = build_discovery_query(Platform.INSTAGRAM, "profile", "@example", 30)
    assert query.username == "example" and query.method == DiscoveryMethod.PROFILE
    query = build_discovery_query(None, "post", "https://www.instagram.com/p/abc/", 30)
    assert query.platform == Platform.INSTAGRAM and query.method == DiscoveryMethod.DIRECT_POST


def test_build_discovery_query_detects_platform_and_rejects_bad_post_target() -> None:
    query = build_discovery_query(None, "profile", "https://www.reddit.com/r/test/", 30)
    assert query.platform == Platform.REDDIT
    with pytest.raises(RunRequestError) as bad_post:
        build_discovery_query(Platform.INSTAGRAM, "post", "not-a-url", 30)
    assert bad_post.value.code == "POST_URL_REQUIRED"
    with pytest.raises(RunRequestError) as blank:
        build_discovery_query(Platform.INSTAGRAM, "profile", "   ", 30)
    assert blank.value.code == "TARGET_REQUIRED"


@pytest.mark.asyncio
async def test_successful_run_emits_required_events_and_verifies_chain() -> None:
    service, chain = make_service()
    record, query = service.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, True)
    final = await service.execute_run(record.run_id, b"selfie", query, "1.0", True)

    assert final.status.value == "COMPLETED"
    assert final.result is not None and final.result.outcome == "VERIFIED"
    assert final.result.blockchain.status == "CONFIRMED"
    assert final.result.blockchain.integrity == "VERIFIED"
    assert final.result.blockchain.tx_hash == "0xabc123"
    assert chain.attested == [final.result.evidence.evidence_sha256]
    names = event_names(service, record.run_id)
    for required in REQUIRED_EVENTS:
        if required == "RUN_FAILED":
            continue
        assert required in names, f"missing {required}"
    assert "RUN_FAILED" not in names
    assert names.index("RUN_STARTED") < names.index("RUN_COMPLETED")
    assert final.candidates and final.candidates[0].status == "ACCEPTED"


@pytest.mark.asyncio
async def test_missing_chain_record_is_surfaced_not_hidden() -> None:
    service, _ = make_service(chain=FakeChain(exists=False))
    record, query = service.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, True)
    final = await service.execute_run(record.run_id, b"selfie", query, "1.0", True)

    assert final.status.value == "COMPLETED"
    assert final.result is not None
    assert final.result.blockchain.integrity == "BLOCKCHAIN_RECORD_NOT_FOUND"
    assert "BLOCKCHAIN_VERIFIED" in event_names(service, record.run_id)


@pytest.mark.asyncio
async def test_attestation_failure_keeps_face_verification_result() -> None:
    service, _ = make_service(chain=FakeChain(attest_error=RuntimeError("RPC_DOWN")))
    record, query = service.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, True)
    final = await service.execute_run(record.run_id, b"selfie", query, "1.0", True)

    assert final.status.value == "COMPLETED"
    assert final.result is not None and final.result.outcome == "VERIFIED"
    assert final.result.blockchain.status == "FAILED"
    assert "BLOCKCHAIN_SUBMISSION_FAILED" in event_names(service, record.run_id)


@pytest.mark.asyncio
async def test_consent_no_face_provider_and_no_match_failures() -> None:
    service, _ = make_service()
    with pytest.raises(RunRequestError) as exc:
        service.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", False, 5, True)
    assert exc.value.code == "CONSENT_REQUIRED"

    no_face, _ = make_service(face=FakeFace(embed_error=ValueError("NO_FACE_FOUND")))
    record, query = no_face.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, False)
    failed = await no_face.execute_run(record.run_id, b"selfie", query, "1.0", False)
    assert failed.status.value == "FAILED" and failed.error_code == "NO_FACE_FOUND"

    multi, _ = make_service(face=FakeFace(embed_error=ValueError("MULTIPLE_FACES")))
    record, query = multi.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, False)
    failed = await multi.execute_run(record.run_id, b"selfie", query, "1.0", False)
    assert failed.error_code == "MULTIPLE_FACES"

    broken, _ = make_service(provider=FakeProvider(error=RuntimeError("APIFY_DOWN")))
    record, query = broken.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, False)
    failed = await broken.execute_run(record.run_id, b"selfie", query, "1.0", False)
    assert failed.error_code == "DISCOVERY_PROVIDER_ERROR"

    empty, _ = make_service(provider=FakeProvider(posts=[]))
    record, query = empty.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, False)
    failed = await empty.execute_run(record.run_id, b"selfie", query, "1.0", False)
    assert failed.error_code == "NO_CANDIDATES"

    wrong_person, _ = make_service(
        face=FakeFace(candidate_vectors=[np.array([0.0, 1.0], dtype=np.float32)])
    )
    record, query = wrong_person.create_run(b"selfie", Platform.INSTAGRAM, "profile", "example", "1.0", True, 5, False)
    failed = await wrong_person.execute_run(record.run_id, b"selfie", query, "1.0", False)
    assert failed.error_code == "NO_VERIFIED_CANDIDATE"
    low = wrong_person.store.get(record.run_id)
    assert low is not None and low.candidates[0].status == "LOW_SCORE"
    assert low.candidates[0].reason == "FACE_MATCH_LOW"


def _api_client(service: RunService) -> TestClient:
    app.dependency_overrides[get_run_service] = lambda: service
    client = TestClient(app)
    client.__enter__()
    return client


def test_api_run_status_sse_preflight_and_diagnostics() -> None:
    import time

    service, _ = make_service()
    client = _api_client(service)
    try:
        response = client.post(
            "/api/runs",
            files={"face_image": ("face.jpg", b"selfie-bytes", "image/jpeg")},
            data={
                "platform": "instagram",
                "mode": "profile",
                "target": "example",
                "consent_accepted": "true",
                "consent_version": "1.0",
                "max_posts": "5",
                "attest": "true",
            },
        )
        assert response.status_code == 202, response.text
        run_id = response.json()["run_id"]

        deadline = time.time() + 30
        status = client.get(f"/api/runs/{run_id}").json()
        while status["status"] == "RUNNING" and time.time() < deadline:
            time.sleep(0.1)
            status = client.get(f"/api/runs/{run_id}").json()
        assert status["status"] == "COMPLETED", status
        assert status["result"]["outcome"] == "VERIFIED"

        stream = client.get(f"/api/runs/{run_id}/events")
        assert stream.status_code == 200
        assert "text/event-stream" in stream.headers["content-type"]
        streamed = [line[7:] for line in stream.text.splitlines() if line.startswith("event: ")]
        for required in ("RUN_STARTED", "CANDIDATE_MATCH_RESULT", "RUN_COMPLETED"):
            assert required in streamed

        preflight = client.post(
            "/api/preflight", files={"face_image": ("face.jpg", b"selfie-bytes", "image/jpeg")}
        )
        assert preflight.json()["ok"] is True

        diagnostics = client.get("/api/diagnostics").json()
        assert diagnostics["blockchain"]["chain_id"] == 84532
        assert diagnostics["face"]["matching_policy"] == "face-threshold-v1"
        assert "apify_api_token" not in diagnostics["apify"]

        missing = client.get("/api/runs/does-not-exist")
        assert missing.status_code == 404 and missing.json()["detail"] == "RUN_NOT_FOUND"

        history = client.get("/api/runs").json()
        assert any(item["run_id"] == run_id for item in history["runs"])
    finally:
        client.__exit__()
        app.dependency_overrides.clear()

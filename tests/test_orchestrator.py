import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from app.discovery.apify_provider import FacebookApifyProvider
from app.discovery.models import DiscoveryMethod, DiscoveryQuery, Platform
from app.face.service import FaceEmbedding
from app.verification.orchestrator import VerificationOrchestrator


FIXTURE = Path(__file__).parent / "fixtures" / "facebook" / "profile_live.json"


def fixture_post():
    item = json.loads(FIXTURE.read_text(encoding="utf-8"))[0]
    provider = FacebookApifyProvider("test-token", "profile", "post")
    return provider._normalize(item)


class FakeProvider:
    def __init__(self, posts):
        self.posts = posts
        self.queries = []

    def discover(self, query):
        self.queries.append(query)
        return self.posts


class FakeFaceService:
    def __init__(self, vectors=None):
        self.vectors = vectors or [np.array([1.0, 0.0], dtype=np.float32)]
        self.embed_calls = 0

    def embed_image(self, image_bytes):
        self.embed_calls += 1
        return FaceEmbedding(
            vector=np.array([1.0, 0.0], dtype=np.float32),
            bbox=(0.0, 0.0, 1.0, 1.0),
            det_score=0.99,
        )

    def embeddings_in_image(self, image_bytes):
        return self.vectors

    @staticmethod
    def cosine_similarity(first, second):
        return float(np.dot(first, second) / (np.linalg.norm(first) * np.linalg.norm(second)))


class FakeBlockchain:
    def __init__(self):
        self.calls = []

    def attest(self, digest):
        self.calls.append(digest)
        return "0xtest-attestation"


@pytest.mark.asyncio
async def test_successful_profile_pipeline_attests_only_evidence_hash():
    provider = FakeProvider([fixture_post()])
    face = FakeFaceService()
    chain = FakeBlockchain()
    fetched = []

    async def fetch(url):
        fetched.append(url)
        return b"candidate-image", "image/jpeg"

    fixed = datetime(2026, 9, 7, tzinfo=timezone.utc)
    query = DiscoveryQuery(
        platform=Platform.FACEBOOK,
        profile_url="https://www.facebook.com/zuck",
        method=DiscoveryMethod.PROFILE,
        max_posts=1,
    )
    result = await VerificationOrchestrator(
        face,
        0.8,
        discovery_provider=provider,
        blockchain_service=chain,
        media_fetcher=fetch,
        image_similarity=lambda first, second: 0.25,
        clock=lambda: fixed,
    ).run(
        b"selfie",
        query=query,
        consent_accepted=True,
        consent_timestamp=fixed,
        attest=True,
    )

    assert provider.queries == [query]
    assert face.embed_calls == 1
    assert fetched == ["https://media.example.test/facebook/photo-1.jpg"]
    assert result.evidence.discovery_method == "profile"
    assert result.evidence.evidence_sha256 is not None
    assert result.evidence.blockchain_evidence_hash == result.evidence.evidence_sha256
    assert chain.calls == [result.evidence.evidence_sha256]
    assert result.attestation_tx_hash == "0xtest-attestation"


@pytest.mark.asyncio
async def test_direct_post_mode_uses_provider_and_rejects_low_face_match():
    post = fixture_post()
    provider = FakeProvider([post])
    query = DiscoveryQuery(
        platform=Platform.FACEBOOK,
        post_url=post.post_url,
        method=DiscoveryMethod.DIRECT_POST,
    )

    async def fetch(url):
        return b"candidate-image", "image/jpeg"

    orchestrator = VerificationOrchestrator(
        FakeFaceService([np.array([0.0, 1.0], dtype=np.float32)]),
        0.8,
        discovery_provider=provider,
        media_fetcher=fetch,
    )

    with pytest.raises(RuntimeError, match="NO_VERIFIED_CANDIDATE"):
        await orchestrator.run(b"selfie", query=query, consent_accepted=True)
    assert provider.queries == [query]


@pytest.mark.asyncio
async def test_media_failure_is_recorded_and_next_candidate_succeeds():
    first = fixture_post()
    second = first.model_copy(deep=True)
    second.media = [second.media[1]]
    calls = []

    async def fetch(url):
        calls.append(url)
        if url.endswith("photo-1.jpg"):
            raise TimeoutError("timed out")
        return b"candidate-image", "image/jpeg"

    result = await VerificationOrchestrator(
        FakeFaceService(),
        0.8,
        media_fetcher=fetch,
        image_similarity=lambda first, second: 0.2,
    ).run(b"selfie", posts=[first, second], consent_accepted=True)

    assert len(result.candidate_failures) == 1
    assert result.candidate_failures[0].reason == "TimeoutError"
    assert calls == [
        "https://media.example.test/facebook/photo-1.jpg",
        "https://media.example.test/facebook/photo-2.jpg",
    ]


@pytest.mark.asyncio
async def test_consent_is_required_when_explicitly_declined():
    with pytest.raises(ValueError, match="CONSENT_REQUIRED"):
        await VerificationOrchestrator(FakeFaceService(), 0.8).run(
            b"selfie", posts=[], consent_accepted=False
        )

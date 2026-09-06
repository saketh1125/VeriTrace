from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from app.evidence.hashing import evidence_hash, sha256_bytes
from app.evidence.models import EvidenceMedia, EvidenceRecord, EvidenceSource, MatchingEvidence
from app.extraction.media_fetcher import fetch_bytes
from app.face.service import FaceEmbedding, FaceService
from app.matching.image import perceptual_similarity
from app.matching.policy import decide
from app.discovery.models import DiscoveryQuery, SocialPost


@dataclass(frozen=True)
class VerifiedMatch:
    post: SocialPost
    media_url: str
    media_type: str
    image_similarity: float
    face_similarity: float
    evidence: EvidenceRecord


class VerificationOrchestrator:
    def __init__(self, face_service: FaceService, face_threshold: float):
        self.face_service = face_service
        self.face_threshold = face_threshold

    async def run(
        self,
        input_image: bytes,
        input_face: FaceEmbedding,
        posts: list[SocialPost],
        discovery_method: str,
        consent_version: str,
        consent_timestamp: datetime,
    ) -> VerifiedMatch:
        ranked_posts = self._rank_posts(input_image, posts)
        for post, media in ranked_posts:
            try:
                media_bytes, _ = await fetch_bytes(str(media.url))
                # v1 verification is image-first. Video is supported by discovery metadata,
                # but video keyframe extraction is a separate increment.
                if media.media_type != "image":
                    continue
                embeddings = self.face_service.embeddings_in_image(media_bytes)
                if not embeddings:
                    continue
                face_similarity = max(
                    self.face_service.cosine_similarity(input_face.vector, candidate)
                    for candidate in embeddings
                )
                image_similarity = perceptual_similarity(input_image, media_bytes)
                decision = decide(face_similarity, self.face_threshold)
                if not decision.verified:
                    continue

                record = EvidenceRecord(
                    source=EvidenceSource(
                        platform=post.platform.value,
                        post_url=str(post.post_url),
                        author_username=post.author_username,
                        author_name=post.author_name,
                        post_id=post.post_id,
                        published_at=post.published_at,
                    ),
                    media=EvidenceMedia(
                        media_url=str(media.url),
                        sha256=sha256_bytes(media_bytes),
                        media_type=media.media_type,
                    ),
                    matching=MatchingEvidence(
                        image_similarity=image_similarity,
                        face_similarity=face_similarity,
                        image_threshold=0.0,
                        face_threshold=self.face_threshold,
                    ),
                    discovery_method=discovery_method,
                    retrieved_at=datetime.now(timezone.utc),
                    consent_version=consent_version,
                    consent_timestamp=consent_timestamp,
                    input_face_embedding_sha256=sha256_bytes(
                        np.asarray(input_face.vector, dtype=np.float32).tobytes()
                    ),
                )
                digest = evidence_hash(record)
                record = record.model_copy(update={"evidence_sha256": digest, "blockchain_evidence_hash": digest})
                return VerifiedMatch(post, str(media.url), media.media_type, image_similarity, face_similarity, record)
            except Exception:
                # Candidate-level failures should not kill the whole discovery run.
                continue
        raise RuntimeError("NO_VERIFIED_CANDIDATE")

    def _rank_posts(self, input_image: bytes, posts: list[SocialPost]) -> list[tuple[SocialPost, object]]:
        scored: list[tuple[float, SocialPost, object]] = []
        for post in posts:
            for media in post.media:
                # No media download yet. URL order is retained; pHash is computed after fetch.
                scored.append((0.0, post, media))
        return [(post, media) for _, post, media in scored]

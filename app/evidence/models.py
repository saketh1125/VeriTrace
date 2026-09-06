from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EvidenceSource(BaseModel):
    platform: str
    post_url: str
    author_username: str | None = None
    author_name: str | None = None
    post_id: str | None = None
    published_at: datetime | None = None


class EvidenceMedia(BaseModel):
    media_url: str
    sha256: str
    media_type: str


class MatchingEvidence(BaseModel):
    image_similarity: float
    face_similarity: float
    image_threshold: float
    face_threshold: float


class EvidenceRecord(BaseModel):
    schema_version: str = "1.0"
    source: EvidenceSource
    media: EvidenceMedia
    matching: MatchingEvidence
    discovery_method: str
    retrieved_at: datetime
    consent_version: str
    consent_timestamp: datetime
    claim_boundary: str = "This record establishes correspondence to the supplied face embedding and integrity of the attested evidence; it does not establish legal identity, authorship, or truthfulness of the post."
    input_face_embedding_sha256: str | None = None
    blockchain_evidence_hash: str | None = None
    evidence_sha256: str | None = None

    def canonical_payload(self) -> dict:
        payload = self.model_dump(mode="json", exclude_none=True)
        payload.pop("blockchain_evidence_hash", None)
        payload.pop("evidence_sha256", None)
        return payload

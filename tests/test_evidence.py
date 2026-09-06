from datetime import datetime, timezone

from app.evidence.hashing import evidence_hash
from app.evidence.models import EvidenceMedia, EvidenceRecord, EvidenceSource, MatchingEvidence


def make_record():
    return EvidenceRecord(
        source=EvidenceSource(platform="instagram", post_url="https://example.com/p/1"),
        media=EvidenceMedia(media_url="https://cdn.example.com/1.jpg", sha256="a" * 64, media_type="image"),
        matching=MatchingEvidence(image_similarity=0.9, face_similarity=0.9, image_threshold=0.7, face_threshold=0.45),
        discovery_method="profile",
        retrieved_at=datetime.now(timezone.utc),
        consent_version="1.0",
        consent_timestamp=datetime.now(timezone.utc),
    )


def test_canonical_hash_is_stable():
    record = make_record()
    assert evidence_hash(record) == evidence_hash(record)

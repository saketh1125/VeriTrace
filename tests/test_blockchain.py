from tests.test_evidence import make_record

from app.evidence.hashing import evidence_hash
from app.verification.verifier import verify_evidence_record, verify_integrity


class FakeRegistry:
    def __init__(self, record: dict):
        self.record = record

    def verify(self, _evidence_hash: str) -> dict:
        return self.record


def test_independent_verification_recomputes_hash_and_reads_chain():
    record = make_record()
    digest = evidence_hash(record)
    attested = record.model_copy(update={"evidence_sha256": digest, "blockchain_evidence_hash": digest})

    assert verify_evidence_record(attested, FakeRegistry({"exists": True})) == "VERIFIED"


def test_modified_evidence_is_tampered_even_if_chain_record_exists():
    record = make_record()
    digest = evidence_hash(record)
    attested = record.model_copy(update={"evidence_sha256": digest, "blockchain_evidence_hash": digest})
    modified = attested.model_copy(update={"consent_version": "2.0"})

    assert verify_evidence_record(modified, FakeRegistry({"exists": True})) == "TAMPERED"


def test_missing_chain_record_has_distinct_status():
    record = make_record()
    digest = evidence_hash(record)

    assert verify_integrity(digest, digest, {"exists": False}) == "BLOCKCHAIN_RECORD_NOT_FOUND"

from __future__ import annotations

from typing import Protocol

from app.evidence.hashing import evidence_hash
from app.evidence.models import EvidenceRecord


class EvidenceRegistryReader(Protocol):
    def verify(self, evidence_hash_hex: str) -> dict:
        ...


def verify_integrity(recomputed_evidence_hash: str, stored_evidence_hash: str, chain_record: dict) -> str:
    if recomputed_evidence_hash != stored_evidence_hash:
        return "TAMPERED"
    if not chain_record.get("exists"):
        return "BLOCKCHAIN_RECORD_NOT_FOUND"
    return "VERIFIED"


def verify_evidence_record(record: EvidenceRecord, registry: EvidenceRegistryReader) -> str:
    """Recompute evidence and independently compare it with the registry commitment."""
    recomputed_hash = evidence_hash(record)
    stored_hash = record.blockchain_evidence_hash or record.evidence_sha256 or ""
    chain_record = registry.verify(recomputed_hash)
    return verify_integrity(recomputed_hash, stored_hash, chain_record)

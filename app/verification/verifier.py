from __future__ import annotations


def verify_integrity(recomputed_evidence_hash: str, stored_evidence_hash: str, chain_record: dict) -> str:
    if recomputed_evidence_hash != stored_evidence_hash:
        return "TAMPERED"
    if not chain_record.get("exists"):
        return "BLOCKCHAIN_RECORD_NOT_FOUND"
    return "VERIFIED"

from __future__ import annotations

import hashlib
import json

from .models import EvidenceRecord


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_evidence_bytes(record: EvidenceRecord) -> bytes:
    return json.dumps(
        record.canonical_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_hash(record: EvidenceRecord) -> str:
    return sha256_bytes(canonical_evidence_bytes(record))

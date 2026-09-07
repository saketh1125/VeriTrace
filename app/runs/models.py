"""Run, event, and result models for the verification run API.

These shapes are the backend side of the frontend SSE contract. The frontend
renders them but never re-derives match, hash, or chain decisions from them.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PipelineStep(StrEnum):
    IDLE = "IDLE"
    VALIDATING_INPUT = "VALIDATING_INPUT"
    PROCESSING_FACE = "PROCESSING_FACE"
    DISCOVERING = "DISCOVERING"
    FETCHING_MEDIA = "FETCHING_MEDIA"
    MATCHING = "MATCHING"
    BUILDING_EVIDENCE = "BUILDING_EVIDENCE"
    ATTESTING = "ATTESTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Event names the SSE stream may emit. Mirrors the locked UI contract.
REQUIRED_EVENTS = (
    "RUN_STARTED",
    "CONSENT_ACCEPTED",
    "FACE_DETECTION_STARTED",
    "FACE_DETECTED",
    "EMBEDDING_CREATED",
    "DISCOVERY_STARTED",
    "DISCOVERY_PROGRESS",
    "DISCOVERY_COMPLETED",
    "MEDIA_FETCH_STARTED",
    "MEDIA_FETCH_COMPLETED",
    "CANDIDATE_MATCH_STARTED",
    "CANDIDATE_MATCH_RESULT",
    "FACE_MATCH",
    "EVIDENCE_CREATED",
    "HASH_COMPUTED",
    "BLOCKCHAIN_SUBMISSION_STARTED",
    "BLOCKCHAIN_SUBMITTED",
    "BLOCKCHAIN_VERIFIED",
    "RUN_COMPLETED",
    "RUN_FAILED",
)

ERROR_EVENTS = frozenset({"RUN_FAILED"})
WARN_EVENTS = frozenset({"FACE_MATCH", "CANDIDATE_MATCH_RESULT", "MEDIA_FETCH_COMPLETED"})


def new_run_id(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    stamp = moment.strftime("%Y%m%d_%H%M%S")
    return f"vr_{stamp}_{secrets.token_hex(3)}"


def event_level(event: str, data: dict[str, Any]) -> str:
    if event in ERROR_EVENTS:
        return "ERROR"
    if event in WARN_EVENTS and isinstance(data.get("decision"), str):
        if data["decision"] not in ("accept", "VERIFIED_MATCH", "accepted"):
            return "WARN"
        return "INFO"
    if event == "MEDIA_FETCH_COMPLETED" and data.get("ok") is False:
        return "WARN"
    return "INFO"


class RunEvent(BaseModel):
    timestamp: datetime
    level: str = "INFO"
    event: str
    run_id: str
    candidate_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class CandidateView(BaseModel):
    candidate_id: str
    post_url: str
    platform: str
    author: str | None = None
    published_at: datetime | None = None
    media_url: str
    media_type: str = "image"
    status: str = "DISCOVERED"
    face_similarity: float | None = None
    image_similarity: float | None = None
    reason: str | None = None


class BlockchainView(BaseModel):
    network: str = "Base Sepolia"
    chain_id: int = 84532
    registry: str | None = None
    evidence_hash: str | None = None
    status: str = "SKIPPED"
    tx_hash: str | None = None
    integrity: str = "PENDING"


class EvidenceView(BaseModel):
    post_url: str
    platform: str
    media_url: str
    media_sha256: str | None = None
    evidence_sha256: str | None = None
    face_similarity: float | None = None
    image_similarity: float | None = None
    face_threshold: float | None = None


class RunResult(BaseModel):
    outcome: str
    evidence: EvidenceView | None = None
    blockchain: BlockchainView = Field(default_factory=BlockchainView)


class RunRecord(BaseModel):
    run_id: str
    status: RunStatus = RunStatus.QUEUED
    pipeline_step: PipelineStep = PipelineStep.IDLE
    platform: str
    method: str
    target: str
    max_posts: int = 30
    attest: bool = True
    consent_version: str = "1.0"
    created_at: datetime
    updated_at: datetime
    duration_ms: int | None = None
    candidate_count: int = 0
    processed_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    candidates: list[CandidateView] = Field(default_factory=list)
    result: RunResult | None = None
    events: list[RunEvent] = Field(default_factory=list)

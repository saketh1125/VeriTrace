"""Run API: start runs, poll status, stream SSE events, preflight faces."""

from __future__ import annotations

import inspect
import json
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.config.settings import settings
from app.discovery.models import Platform
from app.runs.models import RunRecord
from app.runs.service import MAX_FACE_IMAGE_BYTES, RunRequestError, RunService
from app.runs.store import RunStore

router = APIRouter(prefix="/api", tags=["runs"])

_default_service: RunService | None = None


def _face_factory() -> object:
    from app.face.service import FaceService

    return FaceService()


def _blockchain_factory() -> object:
    from app.blockchain.registry import BlockchainRegistry

    if not (
        settings.base_sepolia_rpc_url
        and settings.blockchain_private_key
        and settings.evidence_registry_address
    ):
        raise RuntimeError("BLOCKCHAIN_NOT_CONFIGURED")
    return BlockchainRegistry(
        settings.base_sepolia_rpc_url,
        settings.blockchain_private_key,
        settings.evidence_registry_address,
    )


def get_run_service() -> RunService:
    global _default_service
    if _default_service is None:
        from app.discovery.registry import build_registry

        _default_service = RunService(
            RunStore(),
            build_registry(settings),
            face_factory=_face_factory,  # type: ignore[arg-type]
            blockchain_factory=_blockchain_factory,  # type: ignore[arg-type]
            registry_address=settings.evidence_registry_address,
            face_threshold=settings.face_match_threshold,
        )
    return _default_service


def _summarize(record: RunRecord) -> dict:
    return {
        "run_id": record.run_id,
        "status": record.status.value,
        "pipeline_step": record.pipeline_step.value,
        "platform": record.platform,
        "method": record.method,
        "target": record.target,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "duration_ms": record.duration_ms,
        "candidate_count": record.candidate_count,
        "processed_count": record.processed_count,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "outcome": record.result.outcome if record.result else None,
        "event_count": len(record.events),
    }


def _parse_platform(value: str | None) -> Platform | None:
    if value is None or value.strip() == "":
        return None
    try:
        return Platform(value.strip().lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="UNSUPPORTED_PLATFORM") from None


@router.post("/runs", status_code=202)
async def start_run(
    request: Request,
    face_image: UploadFile = File(...),
    platform: str | None = Form(None),
    mode: str = Form("profile"),
    target: str = Form(...),
    consent_accepted: bool = Form(...),
    consent_version: str = Form("1.0"),
    max_posts: int = Form(30),
    attest: bool = Form(True),
    service: RunService = Depends(get_run_service),
) -> dict:
    del request
    image_bytes = await face_image.read(MAX_FACE_IMAGE_BYTES + 1)
    try:
        record, query = service.create_run(
            image_bytes,
            _parse_platform(platform),
            mode,
            target,
            consent_version,
            consent_accepted,
            max_posts,
            attest,
        )
    except RunRequestError as exc:
        raise HTTPException(status_code=400, detail=exc.code) from exc
    import asyncio

    asyncio.create_task(service.execute_run(record.run_id, image_bytes, query, consent_version, attest))
    return _summarize(record)


@router.get("/runs")
def list_runs(limit: int = 20, service: RunService = Depends(get_run_service)) -> dict:
    return {"runs": [_summarize(record) for record in service.store.list_recent(limit)]}


@router.get("/runs/{run_id}")
def get_run(run_id: str, service: RunService = Depends(get_run_service)) -> dict:
    record = service.store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="RUN_NOT_FOUND")
    return record.model_dump(mode="json")


def _encode_event(index: int, event: object) -> str:
    assert hasattr(event, "event") and hasattr(event, "model_dump")
    payload = json.dumps(event.model_dump(mode="json"), separators=(",", ":"))  # type: ignore[union-attr]
    return f"id: {index}\nevent: {event.event}\ndata: {payload}\n\n"  # type: ignore[union-attr]


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str, request: Request, service: RunService = Depends(get_run_service)
) -> StreamingResponse:
    record = service.store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="RUN_NOT_FOUND")
    raw_last_id = request.headers.get("last-event-id")
    try:
        start_index = int(raw_last_id) + 1 if raw_last_id is not None else 0
    except ValueError:
        start_index = 0
    start_index = max(0, start_index)

    async def generate():  # type: ignore[no-untyped-def]
        current = service.store.get(run_id)
        events = current.events if current else []
        position = min(start_index, len(events))
        for index in range(position, len(events)):
            yield _encode_event(index, events[index])
        position = len(events)
        deadline = time.monotonic() + 300
        while True:
            if await request.is_disconnected():
                break
            current = service.store.get(run_id)
            if current is None:
                break
            while position < len(current.events):
                yield _encode_event(position, current.events[position])
                position += 1
            if current.status.value in {"COMPLETED", "FAILED"}:
                break
            if time.monotonic() > deadline:
                break
            await service.store.wait_for_event_index(run_id, position, timeout=15.0)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/preflight")
async def preflight(
    face_image: UploadFile = File(...),
    service: RunService = Depends(get_run_service),
) -> dict:
    image_bytes = await face_image.read(MAX_FACE_IMAGE_BYTES + 1)
    return await service.preflight_face(image_bytes)


def _face_defaults() -> dict:
    from app.face.service import FaceService

    params = inspect.signature(FaceService.__init__).parameters
    return {name: params[name].default for name in params if name != "self" and params[name].default is not inspect.Parameter.empty}


@router.get("/diagnostics")
def diagnostics(service: RunService = Depends(get_run_service)) -> dict:
    face_defaults = _face_defaults()
    return {
        "api": {"status": "ok"},
        "apify": {"configured": bool(settings.apify_api_token)},
        "face": {
            "model": face_defaults.get("model_name", "buffalo_l"),
            "detection_size": list(face_defaults.get("detection_size", (640, 640))),
            "min_detection_score": face_defaults.get("min_detection_score", 0.5),
            "min_face_size": face_defaults.get("min_face_size", 40),
            "match_threshold": service.face_threshold,
            "matching_policy": "face-threshold-v1",
            "loaded": service.face_loaded,
        },
        "discovery": {
            "default_limit": settings.max_posts_per_profile,
            "max_candidates": settings.max_candidates,
        },
        "blockchain": {
            "network": "Base Sepolia",
            "chain_id": 84532,
            "registry_configured": bool(settings.evidence_registry_address),
            "rpc_configured": bool(settings.base_sepolia_rpc_url),
        },
    }

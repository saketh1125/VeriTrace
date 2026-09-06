from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.config.settings import settings
from app.discovery.models import DiscoveryMethod, DiscoveryQuery, Platform
from app.discovery.registry import build_registry

app = FastAPI(title="HH Goa Face + Content Verification", version="0.1.0")
registry = build_registry(settings)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/discover")
def discover(
    platform: Platform = Form(...),
    method: DiscoveryMethod = Form(...),
    username: str | None = Form(None),
    profile_url: str | None = Form(None),
    post_url: str | None = Form(None),
    consent_version: str = Form(...),
    consent_accepted: bool = Form(...),
    face_image: UploadFile = File(...),
) -> dict:
    if not consent_accepted:
        raise HTTPException(status_code=400, detail="CONSENT_REQUIRED")
    if consent_version != "1.0":
        raise HTTPException(status_code=400, detail="UNSUPPORTED_CONSENT_VERSION")
    if method == DiscoveryMethod.PROFILE and not (username or profile_url):
        raise HTTPException(status_code=400, detail="PROFILE_TARGET_REQUIRED")
    if method == DiscoveryMethod.DIRECT_POST and not post_url:
        raise HTTPException(status_code=400, detail="POST_URL_REQUIRED")

    try:
        # Input image handling is intentionally separated from provider discovery.
        image_bytes = face_image.file.read()
        if not image_bytes:
            raise ValueError("INPUT_INVALID")
        query = DiscoveryQuery(
            platform=platform,
            username=username,
            profile_url=profile_url,
            post_url=post_url,
            max_posts=settings.max_posts_per_profile,
            method=method,
        )
        posts = registry[platform].discover(query)
        return {
            "status": "CANDIDATES_FOUND",
            "candidate_count": len(posts),
            "face_input_bytes": len(image_bytes),
            "candidates": [post.model_dump(mode="json", exclude_none=True) for post in posts[: settings.max_candidates]],
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Platform(StrEnum):
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    REDDIT = "reddit"


class DiscoveryMethod(StrEnum):
    DIRECT_POST = "direct-post"
    PROFILE = "profile"


class MediaAsset(BaseModel):
    url: HttpUrl
    media_type: str = "image"
    thumbnail_url: HttpUrl | None = None
    width: int | None = None
    height: int | None = None


class SocialPost(BaseModel):
    platform: Platform
    post_url: HttpUrl
    post_id: str | None = None
    author_username: str | None = None
    author_name: str | None = None
    published_at: datetime | None = None
    text: str | None = None
    media: list[MediaAsset] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class DiscoveryQuery(BaseModel):
    platform: Platform
    username: str | None = None
    profile_url: HttpUrl | None = None
    post_url: HttpUrl | None = None
    max_posts: int = 30
    method: DiscoveryMethod

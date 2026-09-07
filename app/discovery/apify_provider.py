from __future__ import annotations

from datetime import datetime
from typing import Any

from apify_client import ApifyClient

from .base import SocialContentProvider
from .models import DiscoveryMethod, DiscoveryQuery, MediaAsset, Platform, SocialPost


class DiscoveryProviderError(RuntimeError):
    """Structured failure raised when an Apify run or dataset is not usable."""

    def __init__(self, code: str, actor_id: str, run_id: str | None = None):
        self.code = code
        self.actor_id = actor_id
        self.run_id = run_id
        context = f" actor={actor_id}"
        if run_id:
            context += f" run_id={run_id}"
        super().__init__(f"{code}{context}")


def _first(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=None)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _as_media(value: Any, media_type: str = "image") -> list[MediaAsset]:
    entries: list[tuple[str, str, Any, Any, Any]] = []
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        entries.append((value, media_type, None, None, None))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                entries.append((item, media_type, None, None, None))
            elif isinstance(item, dict):
                candidate = _first(
                    item,
                    "url",
                    "src",
                    "source_url",
                    "displayUrl",
                    "imageUrl",
                    "videoUrl",
                    "downloadUrl",
                )
                if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                    item_type = _first(item, "media_type", "mediaType", "type")
                    normalized_type = (
                        "video" if isinstance(item_type, str) and item_type.lower() in {"video", "reel"} else media_type
                    )
                    thumbnail = _first(item, "thumbnail_url", "thumbnailUrl")
                    width = item.get("width")
                    height = item.get("height")
                    entries.append((candidate, normalized_type, thumbnail, width, height))
    elif isinstance(value, dict):
        candidate = _first(
            value,
            "url",
            "src",
            "source_url",
            "displayUrl",
            "imageUrl",
            "videoUrl",
            "downloadUrl",
        )
        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
            entries.append((candidate, media_type, None, None, None))

    seen: set[str] = set()
    out: list[MediaAsset] = []
    for url, detected_type, thumbnail, width, height in entries:
        if url in seen:
            continue
        seen.add(url)
        out.append(
            MediaAsset.model_validate(
                {
                    "url": url,
                    "media_type": detected_type,
                    "thumbnail_url": (
                        thumbnail
                        if isinstance(thumbnail, str)
                        and thumbnail.startswith(("http://", "https://"))
                        else None
                    ),
                    "width": width if isinstance(width, int) and width > 0 else None,
                    "height": height if isinstance(height, int) and height > 0 else None,
                }
            )
        )
    return out


class ApifySocialProvider(SocialContentProvider):
    def __init__(self, token: str, platform: Platform, profile_actor: str, post_actor: str):
        if not token:
            raise ValueError("APIFY_API_TOKEN is required")
        self.client = ApifyClient(token)
        self.platform = platform
        self.profile_actor = profile_actor
        self.post_actor = post_actor

    def discover(self, query: DiscoveryQuery) -> list[SocialPost]:
        targets: list[str]
        actor_id: str
        if query.method == DiscoveryMethod.DIRECT_POST:
            if not query.post_url:
                raise ValueError("POST_URL_REQUIRED")
            targets = [str(query.post_url)]
            actor_id = self.post_actor
        else:
            target = str(query.profile_url) if query.profile_url else query.username
            if not target:
                raise ValueError("PROFILE_TARGET_REQUIRED")
            targets = [target]
            actor_id = self.profile_actor

        run_input = self._build_input(query.method, targets, query.max_posts)
        run = self.client.actor(actor_id).call(run_input=run_input)
        if run is None:
            raise DiscoveryProviderError("ACTOR_RUN_NOT_RETURNED", actor_id)
        run_id = str(getattr(run, "id", "")) or None
        status = getattr(run, "status", None)
        if status and str(status) != "SUCCEEDED":
            raise DiscoveryProviderError("ACTOR_RUN_FAILED", actor_id, run_id)
        items = self.client.dataset(run.default_dataset_id).list_items().items
        normalized: list[SocialPost] = []
        for item in items:
            if self._is_error_item(item):
                raise DiscoveryProviderError("ACTOR_DATASET_ERROR", actor_id, run_id)
            if not self._valid_item(item):
                continue
            try:
                normalized.append(self._normalize(item))
            except ValueError:
                continue
        return normalized

    def _build_input(self, method: DiscoveryMethod, targets: list[str], max_posts: int) -> dict[str, Any]:
        if self.platform == Platform.INSTAGRAM:
            return {"startUrls": targets, "maxItems": 1 if method == DiscoveryMethod.DIRECT_POST else max_posts}
        if self.platform == Platform.LINKEDIN:
            if method == DiscoveryMethod.DIRECT_POST:
                return {"postUrls": targets, "maxPosts": 1, "includeMedia": True}
            return {"profileUrls": targets, "maxPosts": max_posts, "includeMedia": True}
        if self.platform == Platform.FACEBOOK:
            if method == DiscoveryMethod.DIRECT_POST:
                return {"urls": targets, "includeCommentText": False}
            return {
                "profileUrls": targets,
                "maxPostsPerProfile": max_posts,
                "expandAllPhotos": True,
                "omitPinnedPosts": True,
            }
        if self.platform == Platform.REDDIT:
            return {
                "startUrls": targets,
                "maxPosts": max_posts,
                "includeComments": False,
            }
        raise ValueError(f"Unsupported platform: {self.platform}")

    def _normalize(self, item: dict[str, Any]) -> SocialPost:
        post_url = _first(item, "postUrl", "post_url", "source_url", "url", "permalink", "canonicalUrl", "link")
        if not post_url:
            raise ValueError("Actor result did not contain a canonical post URL")

        author_username = _first(
            item,
            "username",
            "authorUsername",
            "authorHandle",
            "author_public_identifier",
            "source_username",
            "author",
        )
        if isinstance(author_username, dict):
            author_username = _first(author_username, "username", "handle", "publicIdentifier")

        published = _parse_datetime(
            _first(item, "timestamp", "publishTime", "publishedAt", "createdAt", "created_at", "datePosted")
        )
        text = _first(
            item,
            "caption",
            "text",
            "raw_text",
            "selftext",
            "content",
            "body",
            "postText",
            "post_text",
            "title",
            "message",
        )

        media: list[MediaAsset] = []
        for key in (
            "images", "imageUrls", "image_urls", "media", "mediaUrls", "media_urls",
            "attachments", "photoUrls", "photos", "galleryImages", "thumbnailUrl", "thumbnail",
            "image", "mediaUrl",
        ):
            media.extend(_as_media(item.get(key)))
        for key in ("videoUrl", "video_url", "videoHdUrl", "videoSdUrl", "video", "video_urls"):
            media.extend(_as_media(item.get(key), "video"))

        dedup: dict[str, MediaAsset] = {str(m.url): m for m in media}
        return SocialPost(
            platform=self.platform,
            post_url=post_url,
            post_id=(
                str(post_id)
                if (post_id := _first(item, "postId", "post_id", "source_post_id", "id", "shortCode", "shortcode", "urn"))
                else None
            ),
            author_username=str(author_username) if author_username else None,
            author_name=(
                str(author_name)
                if (author_name := _first(item, "authorName", "author_name", "fullName", "source_profile_name", "name"))
                else None
            ),
            published_at=published,
            text=str(text) if text else None,
            media=list(dedup.values()),
            raw=item,
        )

    @staticmethod
    def _valid_item(item: dict[str, Any]) -> bool:
        return isinstance(item, dict) and bool(
            (not item.get("recordType") or item.get("recordType") == "post")
            and _first(item, "postUrl", "post_url", "source_url", "url", "permalink", "canonicalUrl", "link")
        )

    @staticmethod
    def _is_error_item(item: dict[str, Any]) -> bool:
        return bool(item.get("error")) or str(item.get("postId", "")).lower() == "error"


class InstagramApifyProvider(ApifySocialProvider):
    def __init__(self, token: str, profile_actor: str, post_actor: str):
        super().__init__(token, Platform.INSTAGRAM, profile_actor, post_actor)


class LinkedInApifyProvider(ApifySocialProvider):
    def __init__(self, token: str, profile_actor: str, post_actor: str):
        super().__init__(token, Platform.LINKEDIN, profile_actor, post_actor)


class FacebookApifyProvider(ApifySocialProvider):
    def __init__(self, token: str, profile_actor: str, post_actor: str):
        super().__init__(token, Platform.FACEBOOK, profile_actor, post_actor)


class RedditApifyProvider(ApifySocialProvider):
    def __init__(self, token: str, profile_actor: str, post_actor: str):
        super().__init__(token, Platform.REDDIT, profile_actor, post_actor)

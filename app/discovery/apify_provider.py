from __future__ import annotations

from datetime import datetime
from typing import Any

from apify_client import ApifyClient

from .base import SocialContentProvider
from .models import DiscoveryMethod, DiscoveryQuery, MediaAsset, Platform, SocialPost


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
    urls: list[str] = []
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        urls.append(value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                urls.append(item)
            elif isinstance(item, dict):
                candidate = _first(item, "url", "src", "displayUrl", "imageUrl", "videoUrl", "downloadUrl")
                if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                    urls.append(candidate)
    elif isinstance(value, dict):
        candidate = _first(value, "url", "src", "displayUrl", "imageUrl", "videoUrl", "downloadUrl")
        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
            urls.append(candidate)

    seen: set[str] = set()
    out: list[MediaAsset] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        out.append(MediaAsset(url=url, media_type=media_type))
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
            raise RuntimeError(f"Apify Actor failed to return a run: {actor_id}")
        items = self.client.dataset(run.default_dataset_id).list_items().items
        normalized: list[SocialPost] = []
        for item in items:
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
                return {"postUrls": targets, "maxPosts": 1}
            return {"profileUrls": targets, "maxPostsPerProfile": max_posts, "maxItems": max_posts}
        if self.platform == Platform.FACEBOOK:
            if method == DiscoveryMethod.DIRECT_POST:
                return {"urls": targets, "includeCommentText": False}
            return {"profileUrls": targets, "maxPostsPerProfile": max_posts, "expandAllPhotos": True}
        if self.platform == Platform.REDDIT:
            return {
                "urls": targets,
                "maxPostsPerSource": max_posts,
                "includeComments": False,
                "includeMediaLinks": True,
            }
        raise ValueError(f"Unsupported platform: {self.platform}")

    def _normalize(self, item: dict[str, Any]) -> SocialPost:
        post_url = _first(item, "postUrl", "post_url", "url", "permalink", "canonicalUrl", "link")
        if not post_url:
            raise ValueError("Actor result did not contain a canonical post URL")

        author_username = _first(
            item, "username", "authorUsername", "authorHandle", "source_username", "author"
        )
        if isinstance(author_username, dict):
            author_username = _first(author_username, "username", "name", "handle")

        published = _parse_datetime(
            _first(item, "timestamp", "publishTime", "publishedAt", "createdAt", "created_at", "datePosted")
        )
        text = _first(item, "caption", "text", "content", "body", "postText", "post_text", "title", "message")

        media: list[MediaAsset] = []
        for key in (
            "images", "imageUrls", "image_urls", "media", "mediaUrls", "media_urls",
            "attachments", "photoUrls", "photos", "galleryImages", "thumbnailUrl", "thumbnail",
            "image",
        ):
            media.extend(_as_media(item.get(key)))
        for key in ("videoUrl", "video_url", "videoHdUrl", "videoSdUrl", "video"):
            media.extend(_as_media(item.get(key), "video"))

        dedup: dict[str, MediaAsset] = {str(m.url): m for m in media}
        return SocialPost(
            platform=self.platform,
            post_url=post_url,
            post_id=(
                str(post_id)
                if (post_id := _first(item, "postId", "post_id", "id", "shortCode", "urn"))
                else None
            ),
            author_username=str(author_username) if author_username else None,
            author_name=(
                str(author_name)
                if (author_name := _first(item, "authorName", "fullName", "name"))
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
            _first(item, "postUrl", "post_url", "url", "permalink", "canonicalUrl", "link")
        )


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

import json
from pathlib import Path
from types import SimpleNamespace
from pydantic import HttpUrl, TypeAdapter

import pytest

from app.discovery.apify_provider import (
    DiscoveryProviderError,
    FacebookApifyProvider,
    InstagramApifyProvider,
    LinkedInApifyProvider,
    RedditApifyProvider,
)
from app.discovery.models import DiscoveryMethod, DiscoveryQuery, Platform


def test_linkedin_live_profile_fixture_preserves_author_and_video_metadata():
    fixture_path = Path(__file__).parent / "fixtures" / "linkedin" / "profile_live.json"
    item = json.loads(fixture_path.read_text(encoding="utf-8"))[0]

    post = LinkedInApifyProvider("test-token", "profile-actor", "post-actor")._normalize(item)

    assert post.author_username == "satyanadella"
    assert post.media[0].media_type == "video"
    assert str(post.media[0].thumbnail_url) == "https://media.example.test/linkedin/thumbnail.jpg"


def _fixture(platform: str, name: str = "profile_live") -> dict:
    path = Path(__file__).parent / "fixtures" / platform / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))[0]


def test_instagram_live_profile_fixture_normalizes_media():
    post = InstagramApifyProvider("test-token", "profile-actor", "post-actor")._normalize(
        _fixture("instagram")
    )

    assert post.post_id == "3978880184454783667"
    assert len(post.media) == 2
    assert post.media[1].media_type == "video"


def test_facebook_live_profile_fixture_normalizes_source_fields_and_media():
    post = FacebookApifyProvider("test-token", "profile-actor", "post-actor")._normalize(
        _fixture("facebook")
    )

    assert post.post_id == "10117844921640781"
    assert post.author_name == "Mark Zuckerberg"
    assert post.text == "I believe everyone should have access to superintelligence."
    assert len(post.media) == 2
    assert post.media[0].width is None
    assert post.media[1].height == 1760


def test_reddit_live_direct_post_fixture_normalizes_post_only():
    post = RedditApifyProvider("test-token", "profile-actor", "post-actor")._normalize(
        _fixture("reddit", "post_live")
    )

    assert post.post_id == "1vgbkge"
    assert post.author_username == "spez"
    assert post.text == "Modernizing Reddit’s infrastructure with you"
    assert post.media == []


class _FakeClient:
    def __init__(self, run, items):
        self.run = run
        self.items = items

    def actor(self, _actor_id):
        return SimpleNamespace(call=lambda run_input: self.run)

    def dataset(self, _dataset_id):
        return SimpleNamespace(list_items=lambda: SimpleNamespace(items=self.items))


def _query(platform: Platform = Platform.INSTAGRAM) -> DiscoveryQuery:
    profile_url = TypeAdapter(HttpUrl).validate_python("https://example.com/profile")
    return DiscoveryQuery(
        platform=platform,
        method=DiscoveryMethod.PROFILE,
        profile_url=profile_url,
        max_posts=1,
    )


def test_failed_actor_run_is_structured_failure():
    provider = InstagramApifyProvider("test-token", "profile-actor", "post-actor")
    provider.client = _FakeClient(
        SimpleNamespace(id="run-failed", status="FAILED", default_dataset_id="dataset"), []
    )

    with pytest.raises(DiscoveryProviderError) as raised:
        provider.discover(_query())

    assert raised.value.code == "ACTOR_RUN_FAILED"
    assert raised.value.run_id == "run-failed"


def test_provider_error_row_is_not_a_candidate():
    provider = FacebookApifyProvider("test-token", "profile-actor", "post-actor")
    provider.client = _FakeClient(
        SimpleNamespace(id="run-error-row", status="SUCCEEDED", default_dataset_id="dataset"),
        [{"postId": "error", "url": "https://www.facebook.com/NASA/posts/1", "text": "Error"}],
    )

    with pytest.raises(DiscoveryProviderError) as raised:
        provider.discover(_query(Platform.FACEBOOK))

    assert raised.value.code == "ACTOR_DATASET_ERROR"


def test_live_actor_input_contracts_are_bounded_and_platform_specific():
    linkedin = LinkedInApifyProvider("test-token", "profile-actor", "post-actor")
    reddit = RedditApifyProvider("test-token", "profile-actor", "post-actor")

    assert linkedin._build_input(DiscoveryMethod.PROFILE, ["https://www.linkedin.com/in/example/"], 1) == {
        "profileUrls": ["https://www.linkedin.com/in/example/"],
        "maxPosts": 1,
        "includeMedia": True,
    }
    assert reddit._build_input(DiscoveryMethod.DIRECT_POST, ["https://www.reddit.com/r/example/comments/1/post/"], 1) == {
        "startUrls": ["https://www.reddit.com/r/example/comments/1/post/"],
        "maxPosts": 1,
        "includeComments": False,
    }

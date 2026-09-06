from __future__ import annotations

import argparse
import json

from app.config.settings import settings
from app.discovery.models import DiscoveryMethod, DiscoveryQuery, Platform
from app.discovery.registry import build_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="HH Goa Task 3 social-content discovery")
    parser.add_argument("--platform", required=True, choices=[p.value for p in Platform])
    parser.add_argument("--profile")
    parser.add_argument("--post-url")
    parser.add_argument("--max-posts", type=int, default=settings.max_posts_per_profile)
    args = parser.parse_args()

    method = DiscoveryMethod.DIRECT_POST if args.post_url else DiscoveryMethod.PROFILE
    query = DiscoveryQuery(
        platform=Platform(args.platform),
        username=args.profile if args.profile and not args.profile.startswith("http") else None,
        profile_url=args.profile if args.profile and args.profile.startswith("http") else None,
        post_url=args.post_url,
        max_posts=args.max_posts,
        method=method,
    )
    provider = build_registry(settings)[query.platform]
    result = provider.discover(query)
    print(json.dumps([item.model_dump(mode="json", exclude_none=True) for item in result], indent=2))


if __name__ == "__main__":
    main()

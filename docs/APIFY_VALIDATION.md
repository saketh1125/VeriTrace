# Phase 1 Apify validation

Validated 2026-09-06/07 with bounded one-post requests against public targets. Run IDs are retained only as provider troubleshooting references; no credentials or signed media URLs are stored here.

| Platform/mode | Actor run | Result | Observation |
|---|---|---|---|
| Instagram profile | `Ehgy4uAKrYo1J3Vdy` | 1 normalized post, 2 media assets | Profile run succeeded after transient Instagram `401` retries. |
| Instagram direct post | `Zs8qRfh2DREaLqpAA` | 0 posts | Actor completed but could not resolve the post owner; treat as no candidate, not a match. |
| LinkedIn profile | `lSvHvuspUBXP76KPl` | 1 normalized post, 1 media asset | Live schema uses `author_public_identifier` and nested `media[].type`. |
| LinkedIn direct post | `nHRZc9w7Gek2fT9tY` | failed | Actor reported a login/challenge page; adapter exposes `ACTOR_RUN_FAILED`. |
| Facebook profile | `PasuNwRRnrHEZgrg5` | 1 normalized post, 12 media assets | Live schema uses `source_url`, `source_post_id`, `raw_text`, nested `author`, and `media[].source_url`. |
| Facebook direct post | `P1pfZ4cDQkeEtgxaq` | provider error row | Actor returned `postId: "error"` and `net::ERR_TUNNEL_CONNECTION_FAILED`; adapter exposes `ACTOR_DATASET_ERROR`. |
| Reddit profile | `sND0I7ppyhr3888zY` | no post candidates | Actor fell back to RSS and returned profile/comment records; non-`post` records are ignored. |
| Reddit direct post | `FdRilDFPHIkW6hJ8M` | 1 normalized post, 0 media assets | Direct public text post resolves; it is correctly ineligible for media face verification. |

Sanitized response fixtures and normalization tests live under `tests/fixtures/` and `tests/test_discovery_normalization.py`. Media URLs in fixtures are deliberately replaced with non-routable example hosts; the Instagram live thumbnail was separately fetched through `MediaFetcher` as `image/jpeg` (31,998 bytes).

The pinned community Actors remain replaceable integrations. These observations are validation evidence, not availability guarantees.

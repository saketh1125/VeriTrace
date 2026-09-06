# Data Contracts

## 1. DiscoveryQuery

The normalized request sent to a platform adapter.

```python
DiscoveryQuery(
    platform=Platform.INSTAGRAM,
    method=DiscoveryMethod.PROFILE,
    username="example",
    profile_url=None,
    post_url=None,
    max_posts=30,
)
```

Invariant: exactly one discovery target is supplied for the selected method.

## 2. MediaAsset

Normalized candidate media:

```text
url
media_type: image | video | other
thumbnail_url?
width?
height?
```

Provider-specific media fields stay in `SocialPost.raw` when useful for debugging/fixture development.

## 3. SocialPost

Platform-neutral representation:

```text
platform
post_url
post_id?
author_username?
author_name?
published_at?
text?
media[]
raw
```

`post_url` is mandatory for evidence provenance. Unknown metadata remains absent rather than fabricated.

## 4. CandidateMatch

Internal matching result:

```text
post
media
image_similarity?
best_face_similarity
matched_face_index
face_threshold
accepted
```

`accepted` is derived from the match policy and must not be supplied by a platform provider.

## 5. EvidenceRecord

The evidence record captures:

```text
schema_version
claim_boundary
source provenance
selected media provenance
selected media SHA-256
matching metrics and thresholds
discovery method
retrieval timestamp
consent version/timestamp
```

Example:

```json
{
  "schema_version": "1.0",
  "claim_boundary": "face-content correspondence; not legal identity or authorship",
  "source": {
    "platform": "instagram",
    "post_url": "https://example.invalid/p/abc",
    "post_id": "abc",
    "author_username": "example",
    "published_at": "2026-09-06T12:00:00Z"
  },
  "media": {
    "media_type": "image",
    "media_url": "https://example.invalid/media.jpg",
    "sha256": "..."
  },
  "matching": {
    "image_similarity": 0.81,
    "face_similarity": 0.87,
    "face_threshold": 0.45
  },
  "retrieval": {
    "discovery_method": "profile",
    "retrieved_at": "2026-09-06T12:01:00Z"
  },
  "consent": {
    "version": "1.0",
    "accepted_at": "2026-09-06T12:00:00Z"
  }
}
```

Do not store a raw selfie or face embedding in the evidence payload.

## 6. Canonical hashing

Canonical JSON requirements:

- UTF-8.
- sorted keys.
- compact separators.
- deterministic field omission for absent values.
- fields derived from the hash (`evidence_sha256`, transaction identifiers, explorer URLs) are excluded from the preimage.

The canonical bytes are then hashed with SHA-256.

The media SHA-256 is computed from the exact bytes downloaded and selected for verification.

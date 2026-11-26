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

Note: `DiscoveryQuery` does not enforce a single-target validator; `ApifySocialProvider.discover` selects `post_url` for `direct-post` and `profile_url` (falling back to `username`) for `profile`.

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

## 4. Matching and Candidate Models

Implemented matching and candidate models (`MatchDecision`, `VerifiedMatch`, `CandidateView`):

```text
MatchDecision: verified, reason
VerifiedMatch: post, media_url, media_type, image_similarity, face_similarity, evidence, attestation_tx_hash?, candidate_failures
CandidateView: candidate_id, post_url, platform, author?, published_at?, media_url, media_type, status, face_similarity?, image_similarity?, reason?
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
  "claim_boundary": "This record establishes correspondence to the supplied face embedding and integrity of the attested evidence; it does not establish legal identity, authorship, or truthfulness of the post.",
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
    "image_threshold": 0.0,
    "face_threshold": 0.45
  },
  "discovery_method": "profile",
  "retrieved_at": "2026-09-06T12:01:00Z",
  "consent_version": "1.0",
  "consent_timestamp": "2026-09-06T12:00:00Z",
  "input_face_embedding_sha256": null,
  "blockchain_evidence_hash": null,
  "evidence_sha256": null
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

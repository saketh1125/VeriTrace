# Locked Architecture

**Status:** Locked for implementation v1

## 1. Product definition

The application establishes whether a consented input face appears in public social content located by a user-supplied social target.

This system establishes **content/face correspondence**. It does not establish legal identity, authorship, ownership, consent of other depicted people, account ownership, or truthfulness of the content.

## 2. Supported discovery modes

### A. Direct post
The user supplies a public post URL. The platform adapter fetches that exact post and its public media.

### B. Public profile
The user supplies a platform plus username/profile URL. The adapter enumerates a bounded number of public posts, returning canonical post URLs and media URLs where available.

### C. Reverse-image fallback
Generic reverse-image search is an optional fallback provider. It is not a critical path and cannot be promoted to one without a benchmark and ADR.

## 3. End-to-end workflow

```text
Consent + Face Image + Platform + (Post URL | Profile)
                         |
                         v
                  FastAPI / CLI
                         |
            +------------+-------------+
            |                          |
            v                          v
     FaceService                 DiscoveryService
  detect + embed locally        platform adapter
            |                          |
            |                    Apify Actor
            |                          |
            |                    normalized posts
            |                          |
            +------------+-------------+
                         |
                         v
                    Candidate Posts
                         |
                         v
                    Media Fetcher
                  HTTPS / SSRF guards
                         |
                         v
                   Candidate Media
                         |
               +---------+---------+
               |                   |
               v                   v
        Image Similarity      Face Detection
        pHash / ranking       + Face Embedding
               |                   |
               +---------+---------+
                         |
                         v
                    Match Policy
                         |
                    face threshold
                         |
                 +-------+-------+
                 |               |
               reject          match
                 |               |
                 v               v
            next candidate    EvidenceRecord
                                  |
                               SHA-256
                                  |
                                  v
                           Base Sepolia
                         EvidenceRegistry
                                  |
                                  v
                      Independent Verification
                                  |
                         VERIFIED / TAMPERED
```

## 4. Component responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| `api` | HTTP input/output, request validation, orchestration entrypoint | Platform-specific scraping logic |
| `cli` | Local operator workflow using same services as API | Duplicate verification logic |
| `discovery` | Resolve supplied public social target into normalized posts/media | Decide face identity |
| `extraction` | Download/validate media and later extract video frames | Trust arbitrary URLs |
| `face` | Detect faces, quality checks, create embeddings | Search the web |
| `matching` | Similarity metrics and acceptance policy | Call social APIs |
| `evidence` | Canonical evidence model + deterministic hashing | Write arbitrary chain state |
| `blockchain` | Submit/read evidence commitments | Store biometric material |
| `verification` | Coordinate candidate processing and independent chain verification | Become a platform scraper |

## 5. Provider boundary

`SocialContentProvider` is the only platform-facing contract used by core verification code.

Current adapters:

```text
InstagramApifyProvider
LinkedInApifyProvider
FacebookApifyProvider
RedditApifyProvider
```

Apify Actor IDs and Actor-specific input/output details are configuration/integration details. They must remain confined to `app/discovery`.

### Current v1 Actor targets

| Platform | Profile discovery | Direct post |
|---|---|---|
| Instagram | `parseforge/instagram-posts-scraper` | `parseforge/instagram-posts-scraper` |
| LinkedIn | `data-slayer/linkedin-profile-posts-scraper` | `fetch_cat/linkedin-posts-scraper` |
| Facebook | `spbotdel/facebook-profile-posts-all-photos-scraper` | `scrapyspider/facebook-post-scraper` |
| Reddit | `scrapers_lat/reddit-scraper` | `scrapers_lat/reddit-scraper` |

These are community-maintained Apify integrations, not official platform APIs. Their availability and schemas must be validated live and may be replaced without changing the domain model.

Current capability references:
- Instagram: https://apify.com/parseforge/instagram-posts-scraper
- LinkedIn profile posts: https://apify.com/data-slayer/linkedin-profile-posts-scraper
- LinkedIn direct posts: https://apify.com/fetch_cat/linkedin-posts-scraper
- Facebook profile posts/photos: https://apify.com/spbotdel/facebook-profile-posts-all-photos-scraper

## 6. Discovery execution

The user target is normalized into `DiscoveryQuery`.

For a direct post, invoke only the direct-post Actor with a bounded single-item request.

For a profile, invoke only the profile Actor with a bounded post count.

The raw Actor dataset is converted into `SocialPost` immediately. Downstream services never depend on Actor-specific field names.

A candidate post is eligible for media verification only when it has a canonical public post URL and at least one supported media asset.

## 7. Media handling

Media URLs returned by providers are untrusted.

`MediaFetcher` enforces:

- HTTPS-only URLs.
- DNS/IP validation against private/internal ranges.
- connection/read timeouts.
- maximum response size.
- content-type validation.
- no arbitrary file execution.
- no unbounded redirects in the initial implementation.

Images are processed directly. Video is represented in the domain now and will be supported by bounded keyframe extraction before being accepted as a full v1 verification path.

## 8. Face processing

Input:

```text
face image -> detect face -> quality checks -> ArcFace embedding -> normalized vector
```

Candidate image:

```text
candidate media -> detect all faces -> embed each face -> compare against input embedding
```

Acceptance is based on the best candidate-face similarity crossing a calibrated threshold.

Multiple faces are allowed in candidate media. Multiple faces in the input are rejected in v1 because the user is expected to provide one subject face.

## 9. Similarity policy

Face similarity is the **primary identity/correspondence gate**.

Perceptual image similarity (pHash) is a **ranking/corroboration signal**. It is not required for a valid face match because background, crop, lighting, pose and scene can change substantially.

Do not use exact embedding-vector equality. Use the similarity metric appropriate to the selected model (cosine similarity for the current implementation).

## 10. Evidence lifecycle

For a verified candidate:

```text
post metadata + selected media + matching scores + retrieval context
                               |
                               v
                       canonical EvidenceRecord
                               |
                         SHA-256(evidence)
                               |
                               v
                     Base Sepolia commitment
```

The selected candidate media bytes also receive a separate SHA-256 digest.

Missing metadata is represented as `null`/omitted; it is never invented.

## 11. Blockchain boundary

Network: **Base Sepolia** (chain ID `84532`).

Contract: `EvidenceRegistry.sol`.

Stored commitment:

```text
bytes32 evidenceHash
attester
attestedAt
```

No raw image, selfie, embedding, biometric template, caption dump, or private social data is written on-chain.

## 12. Independent verification

The verifier must:

1. Load the evidence record.
2. Reproduce canonical serialization.
3. Recompute SHA-256.
4. Read the expected commitment from the registry.
5. Compare the two values.

Results:

- `VERIFIED`
- `TAMPERED`
- `BLOCKCHAIN_RECORD_NOT_FOUND`

The verifier must not rely on a cached UI status from the attestation step.

## 13. Boundaries that are intentionally not part of v1

- Global face-to-internet search as a primary discovery mechanism.
- Persistent biometric databases.
- Vector databases such as Pinecone.
- Public production hosting.
- Background job infrastructure.
- Large frontend framework unless the thin UI proves insufficient.

Each can be reconsidered through an ADR only when a concrete requirement justifies it.

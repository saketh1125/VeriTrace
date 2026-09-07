# Hacker House Goa 2026 — Task 3

**Face Identification → User-Directed Public Social Discovery → Independent Face Verification → Blockchain Attestation**

## What this builds

A consent-first pipeline that:

1. accepts a face scan from the user;
2. accepts a public social post URL or public profile/username;
3. retrieves public candidate posts through a platform adapter;
4. fetches candidate media;
5. independently detects/encodes faces and verifies correspondence with the input face;
6. creates a deterministic evidence record;
7. commits the evidence hash to Base Sepolia;
8. independently re-hashes the evidence and verifies the on-chain commitment.

**Claim boundary:** this demonstrates face-to-content correspondence. It does not prove legal identity, authorship, account ownership, consent of other depicted people, or truthfulness of content.

## Locked stack

- Python 3.11+
- FastAPI
- Pydantic
- InsightFace / ArcFace + ONNX Runtime
- OpenCV + Pillow
- ImageHash (pHash)
- Apify Python client
- HTTPX
- Web3.py
- Solidity 0.8.24
- Base Sepolia (chain ID `84532`)
- pytest + Ruff + mypy

## Architecture

```text
Face Scan + Consent + Social Target
                 |
                 v
         FastAPI / CLI
          |          |
          v          v
     FaceService   DiscoveryService
          |          |
          |       Apify Actor
          |          |
          |      SocialPost[]
          |          |
          +-----> Candidate Media
                       |
                  MediaFetcher
                       |
               +-------+-------+
               |               |
          Image ranking    Face matching
               |               |
               +-------+-------+
                       |
                  Match Policy
                       |
                  EvidenceRecord
                       |
                    SHA-256
                       |
                  Base Sepolia
                       |
              Independent verifier
                       |
                 VERIFIED / TAMPERED
```

See `docs/ARCHITECTURE.md` for the locked design.

## Apify integrations

Current v1 targets:

| Platform | Profile | Direct post |
|---|---|---|
| Instagram | `parseforge/instagram-posts-scraper` | `parseforge/instagram-posts-scraper` |
| LinkedIn | `data-slayer/linkedin-profile-posts-scraper` | `fetch_cat/linkedin-posts-scraper` |
| Facebook | `spbotdel/facebook-profile-posts-all-photos-scraper` | `scrapyspider/facebook-post-scraper` |
| Reddit | `scrapers_lat/reddit-scraper` | `scrapers_lat/reddit-scraper` |

These Actors are community-maintained integrations. Their IDs live in configuration and their raw responses are normalized immediately behind the provider interface. Live validation is required before treating an Actor as a stable dependency.

Actor references:
- Instagram: https://apify.com/parseforge/instagram-posts-scraper
- LinkedIn profile posts: https://apify.com/data-slayer/linkedin-profile-posts-scraper
- LinkedIn direct posts: https://apify.com/fetch_cat/linkedin-posts-scraper
- Facebook profile posts/photos: https://apify.com/spbotdel/facebook-profile-posts-all-photos-scraper

## Repository map

```text
app/
  api/             HTTP boundary
  cli/             local operator workflow
  config/          environment/configuration
  discovery/       Apify/platform adapters + normalization
  extraction/      secure candidate media fetching
  face/            face detection/embedding
  matching/        similarity + match policy
  evidence/        evidence model + canonical hashing
  blockchain/      Base Sepolia contract client
  verification/    end-to-end orchestration
  runs/            run lifecycle + SSE event contract (`docs/RUN_API.md`)
contracts/         Solidity registry
scripts/            deployment utilities
frontend/          thin verification console (React + Vite, backend is source of truth)
docs/               durable architecture/security/data/development docs
adr/                accepted architecture decisions
tests/              unit/integration/fixture tests
AGENTS.md           Codex project guide
```

## Local setup

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env
```

Set `APIFY_API_TOKEN` for live provider tests. Set RPC/wallet variables only for blockchain tests/deployment.

Run tests:

```bash
pytest -q
```

Run API:

```bash
uvicorn app.api.main:app --reload
```

Run CLI:

```bash
python -m app.cli.main --platform instagram --profile example --max-posts 10
```

## Development order

### InsightFace / ONNX Runtime setup

Install the project dependencies (including the local InsightFace and ONNX Runtime adapter):

```bash
python -m pip install -e ".[dev]"
```

The first `FaceService()` construction downloads the configured InsightFace `buffalo_l`
model pack into InsightFace's local model cache. It runs CPU-only by default. To smoke-test
the real runtime against an image containing exactly one clear face, run:

```bash
python -m app.face.smoke_test path/to/face.jpg
```

The smoke test reports only embedding dimensions and detection score; it never prints or
persists the embedding. Runtime initialization failures are surfaced as
`INSIGHTFACE_INITIALIZATION_FAILED`.

### Phase 1 — Live Apify validation (current)

Run each pinned Actor against a known public profile and known public post, inspect the actual dataset JSON, freeze sanitized fixtures, and harden normalization.

### Phase 2 — Face runtime

Install/model-load InsightFace and add face quality gates plus calibrated similarity thresholds.

### Phase 3 — Media extraction

Finish image/carousel support and bounded video keyframe extraction.

### Phase 4 — Verification orchestration

Wire discovery → media → face matching → evidence into one end-to-end service.

### Phase 5 — Blockchain

Deploy `EvidenceRegistry.sol` to Base Sepolia, attest evidence hashes, then independently verify them.

### Phase 6 — Thin UI

Add consent, image input, platform target, progress, candidate results, and blockchain verification status.

See `docs/DEVELOPMENT.md` for acceptance criteria.

Phase 1 live Actor results and known provider quirks are recorded in [`docs/APIFY_VALIDATION.md`](docs/APIFY_VALIDATION.md).

## Security/privacy

Read `docs/SECURITY_PRIVACY.md` before adding external integrations. The most important rules are:

- explicit consent before biometric processing;
- no raw biometric data on-chain;
- provider output and public URLs are untrusted;
- secure media fetching with SSRF defenses;
- no private-account access or access-control bypass;
- secrets only through environment/secrets storage.

## Codex

`AGENTS.md` is intentionally short. It is a map to the durable repository knowledge rather than an encyclopedia. Codex should read the relevant `docs/` and `adr/` files before modifying architecture-sensitive code.

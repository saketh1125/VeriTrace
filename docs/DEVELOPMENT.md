# Development Plan

## Phase 0 — Repository foundation

Complete:
- domain contracts
- provider boundary
- secure media fetcher
- similarity policy
- evidence hashing
- blockchain contract/client skeleton
- API/CLI scaffolding
- tests for pure logic

Acceptance: repository installs; targeted pure-logic tests pass.

## Phase 1 — Live Apify validation (current)

For each pinned Actor:

1. Use a known public test profile.
2. Run a bounded profile request.
3. Run a known direct post request where the Actor supports it.
4. Capture the actual dataset JSON.
5. Sanitize credentials/private information.
6. Save a fixture under `tests/fixtures/<platform>/`.
7. Update the normalizer against the real response, not guessed field names.
8. Record any Actor quirks in the relevant adapter and/or ADR.

Acceptance:
- real public profile returns normalized `SocialPost` objects;
- known public post resolves to one normalized post where supported;
- media URLs are present and fetchable for the test fixture;
- fixture-based normalization tests pass;
- provider failure is surfaced as a structured failure, not a false match.

## Phase 2 — Face runtime

Integrate InsightFace/ArcFace + ONNX Runtime locally.

Implement:
- model bootstrap
- one-face input rule
- face quality checks
- candidate multi-face detection
- deterministic embedding normalization
- configurable similarity threshold

Acceptance:
- true-match fixture passes;
- wrong-person fixture fails;
- no-face fixture fails cleanly;
- multi-face input is rejected cleanly.

## Phase 3 — Media extraction

Implement:
- image decoding
- supported format validation
- carousel/image-set handling
- bounded video keyframe extraction

Acceptance:
- each returned media asset is independently processable;
- unsupported/broken assets produce structured failures.

## Phase 4 — Verification orchestrator

Implement:

```text
query -> discovery -> candidate iteration -> media fetch -> face match -> evidence
```

Candidate loop must:
- honor configured post/media bounds;
- stop on the first sufficiently strong verified candidate;
- continue after candidate-level rejection;
- preserve structured failure reasons.

Acceptance: one command can complete a full verification run from a fixture-backed provider.

## Phase 5 — Blockchain

Implement:
- contract deployment script
- evidence attestation
- transaction receipt persistence
- independent verification

Acceptance:
- local evidence hash matches the on-chain record;
- modified evidence produces `TAMPERED`;
- missing chain record produces `BLOCKCHAIN_RECORD_NOT_FOUND`.

## Phase 6 — Thin UI

Build a small browser UI around the API:

```text
consent -> image input -> platform target -> run -> candidate progress -> result -> chain verification
```

Do not introduce a large frontend architecture unless needed.

## Phase 7 — Demonstration hardening

Create golden scenarios:

- true face match;
- wrong person on correct post;
- visually similar background but wrong person;
- multiple people in candidate media;
- no face;
- private/inaccessible profile;
- broken media URL;
- provider failure;
- blockchain success;
- blockchain mismatch.

Record one clean screen-capture path that demonstrates the complete pipeline.

# ADR 0009 — Run/Event SSE Contract and Thin Verification Console

**Status:** Accepted
**Date:** 2026-09-07
**Relates to:** AGENTS.md rule 12, docs/ARCHITECTURE.md §4, docs/DEVELOPMENT.md Phase 6,
`VeriTrace-Frontend-Implementation-Guide.docx` v1.0 (LOCKED UI contract)

## Context

The pipeline (discovery → media → face match → evidence → attestation →
independent verification) was only drivable via CLI and a single
`POST /v1/discover` endpoint with no progress, candidate, or log visibility.
The locked frontend guide requires a run API with Server-Sent Events so a
small operator console can render pipeline state, candidates, evidence, and
chain verification live. AGENTS.md rule 12 forbids adding a React app without
a demonstrated need.

## Decision

1. Add a backend run contract under `app/runs/` plus routes in `app/api/runs.py`:
   `POST /api/runs`, `GET /api/runs`, `GET /api/runs/{run_id}`,
   `GET /api/runs/{run_id}/events` (`text/event-stream`), `POST /api/preflight`,
   `GET /api/diagnostics`. Full field contract lives in `docs/RUN_API.md`.
2. Reuse the single `VerificationOrchestrator` candidate loop through an
   opt-in `EventSink` observer. No matching, hashing, or chain logic is
   duplicated for streaming; `events=None` preserves old behavior exactly.
3. Runs stay in process memory (bounded history). No queue, cache, vector DB,
   or hosted database is introduced.
4. Accept a `frontend/` Vite + React console as the demonstrated need behind
   rule 12: it is the DEVELOPMENT.md Phase 6 thin UI, implements only the
   locked guide, performs no face/discovery/hash/chain decisions, and keeps
   the backend as the single source of truth.
5. Two additive event names beyond the guide's required list are emitted and
   documented in `docs/RUN_API.md`: `BLOCKCHAIN_SUBMISSION_FAILED`
   (attestation failure must not fail a face-verified run) and the
   `FACE_MATCH` alias of `CANDIDATE_MATCH_RESULT` (the guide's §9/§10 examples
   use `FACE_MATCH`).

## Consequences

- The UI contract is implementable without backend redesign; routing changes
  stay inside the frontend API adapter.
- `VerificationOrchestrator` gains event hooks; existing tests pass unchanged.
- SSE reconnect rule: clients `GET /api/runs/{run_id}` first, then resume the
  stream from `Last-Event-ID`, so no UI state depends on missed events.

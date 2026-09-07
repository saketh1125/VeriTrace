# Run API + SSE Contract

Backend side of `VeriTrace-Frontend-Implementation-Guide.docx` §10. The
frontend renders these shapes through an isolated API adapter and never
re-derives match, hash, or chain decisions.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/runs` | Start a run (`multipart/form-data`). Returns `202` + run summary. |
| `GET` | `/api/runs?limit=` | Recent runs: id, status, outcome, time, duration. |
| `GET` | `/api/runs/{run_id}` | Full run: status, pipeline step, candidates, result, error, event history. |
| `GET` | `/api/runs/{run_id}/events` | `text/event-stream` SSE feed. Supports `Last-Event-ID` resume. |
| `POST` | `/api/preflight` | One-face upload check. Never returns embeddings. |
| `GET` | `/api/diagnostics` | Model/threshold/limit/network info. Booleans only for secrets. |
| `GET` | `/health` | Unchanged liveness probe. |

### POST /api/runs fields

`face_image` (file, required, ≤10 MB), `platform` (optional; omit to
auto-detect from URL), `mode` (`profile` default | `post`), `target`
(required: username, profile URL, or post URL), `consent_accepted` (must be
`true`), `consent_version` (`1.0`), `max_posts` (default 30, clamped 1–50),
`attest` (default `true`).

Validation failures return `400` with a structured `detail` code
(`CONSENT_REQUIRED`, `TARGET_REQUIRED`, `POST_URL_REQUIRED`,
`UNSUPPORTED_PLATFORM`, `INPUT_INVALID`, `UNSUPPORTED_CONSENT_VERSION`).
Unknown runs return `404` (`RUN_NOT_FOUND`).

### Pipeline steps

`IDLE → VALIDATING_INPUT → PROCESSING_FACE → DISCOVERING → FETCHING_MEDIA →
MATCHING → BUILDING_EVIDENCE → ATTESTING (optional) → VERIFYING →
COMPLETED`, with `FAILED` as the terminal error state. The stepper mirrors
these values verbatim.

### SSE frame

```text
id: 12
event: CANDIDATE_MATCH_RESULT
data: {"timestamp":"...","level":"INFO","event":"CANDIDATE_MATCH_RESULT","run_id":"vr_...","candidate_id":"cand_01","data":{...}}

```

Event names: `RUN_STARTED`, `CONSENT_ACCEPTED`, `FACE_DETECTION_STARTED`,
`FACE_DETECTED`, `EMBEDDING_CREATED`, `DISCOVERY_STARTED`,
`DISCOVERY_PROGRESS`, `DISCOVERY_COMPLETED`, `MEDIA_FETCH_STARTED`,
`MEDIA_FETCH_COMPLETED`, `CANDIDATE_MATCH_STARTED`,
`CANDIDATE_MATCH_RESULT`, `FACE_MATCH` (alias of the result, same payload),
`EVIDENCE_CREATED`, `HASH_COMPUTED`, `BLOCKCHAIN_SUBMISSION_STARTED`,
`BLOCKCHAIN_SUBMITTED`, `BLOCKCHAIN_VERIFIED`, `RUN_COMPLETED`,
`RUN_FAILED`, plus `BLOCKCHAIN_SUBMISSION_FAILED` (`{reason}` or
`{stage:"verification", reason}`) when attestation or the independent chain
read fails without invalidating a face-verified result.

### Candidate statuses

`DISCOVERED`, `PROCESSING`, `ACCEPTED` (`VERIFIED_MATCH`), `LOW_SCORE`
(`FACE_MATCH_LOW`), `NO_FACE` (`NO_FACE_IN_MEDIA`), `MEDIA_FAILED`
(`MEDIA_FETCH_FAILED:<cause>`), `SKIPPED` (`UNSUPPORTED_MEDIA_TYPE`).

### Result semantics

- `result.outcome == "VERIFIED"` means the face gate passed and evidence was
  built. Blockchain submission is reported separately in
  `result.blockchain` (`status`: `CONFIRMED`/`SUBMITTED`/`FAILED`/`SKIPPED`;
  `integrity`: `VERIFIED`/`TAMPERED`/`BLOCKCHAIN_RECORD_NOT_FOUND`/`PENDING`/`UNKNOWN`).
- Final integrity always comes from recomputed-evidence-hash versus the
  on-chain commitment, never from cached submission state.

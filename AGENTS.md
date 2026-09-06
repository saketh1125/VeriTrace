# Codex Project Guide — Hacker House Goa 2026 Task 3

## Mission
Build Task 3 as a small, production-minded verification pipeline:
consented face scan -> user-directed public social discovery -> independent face verification -> evidence hash -> blockchain attestation -> independent verification.

## Source of truth
Use the repository as the durable source of truth. Start with:
- `README.md` — product contract and runnable overview.
- `docs/ARCHITECTURE.md` — locked component boundaries and workflow.
- `docs/DATA_CONTRACTS.md` — normalized data shapes and hashing rules.
- `docs/SECURITY_PRIVACY.md` — security/privacy requirements.
- `docs/DEVELOPMENT.md` — implementation order and acceptance criteria.
- `adr/` — accepted architectural decisions. Do not silently contradict an accepted ADR.

Read the relevant document before changing behavior in that area.

## Non-negotiable architecture
1. User supplies a public post URL OR public profile/username.
2. Apify is an integration mechanism behind `app/discovery`; it is not a domain dependency.
3. Platform output is untrusted candidate data. It never declares a face match.
4. Normalize provider output into `SocialPost` immediately.
5. Candidate media is fetched separately and validated by our application.
6. Local face detection/embedding performs identity correspondence. The face signal is the acceptance gate.
7. Perceptual/image similarity is supporting/ranking evidence, never the sole identity gate.
8. Never put selfies, face embeddings, or raw biometric templates on-chain.
9. The blockchain stores a commitment to the evidence, not the underlying biometric data.
10. Verification must recompute the evidence hash and independently read the chain.
11. Reverse-image search is optional fallback; it must not become a critical dependency without a new ADR and benchmark.
12. Do not add infrastructure (vector DB, queue, cache, React app, hosted database, etc.) without a demonstrated need.

## Provider rules
- Keep all Actor IDs, Actor input schemas, and Actor-specific field mapping inside `app/discovery`.
- Treat Actor schemas as unstable third-party contracts.
- Preserve raw provider payloads for debugging/fixtures where safe; never fabricate missing metadata.
- Prefer bounded requests (`max_posts` or equivalent) and stop as soon as a verified candidate is found.
- Use fixtures from real provider responses for normalizer tests. Do not hardcode a successful match into application logic.
- If a pinned Actor becomes unavailable, replace it behind the same provider interface and document the change.

## Security rules
- Secrets only via environment variables/local secret stores; never commit `.env` or credentials.
- Public URLs are untrusted input.
- HTTPS-only media fetching.
- Enforce timeouts, response-size limits, content-type validation, and SSRF/private-network blocking.
- Do not execute downloaded content.
- Do not access private accounts, bypass authentication, or circumvent access controls.
- Keep biometric processing local in v1 when practical.
- Explicit consent is required before biometric processing.

## Coding rules
- Python 3.11+; type annotations on public functions.
- Prefer small modules and explicit dependencies over magic/global state.
- Keep platform-specific code out of matching/evidence/blockchain modules.
- Raise/return structured domain errors; do not hide failures behind generic success responses.
- Avoid broad exception swallowing. Log enough context to debug without logging secrets or raw biometric data.
- Do not rewrite working architecture merely to make a task easier.
- Update docs/ADRs when a decision changes.

## Testing rules
Before claiming a task is complete:
1. Run the targeted tests.
2. Run the full test suite.
3. Run lint/type checks when configured.
4. For provider changes, add/refresh a sanitized fixture and test normalization.
5. For blockchain changes, test both successful attestation and failed/mismatched verification paths.
6. Do not claim live integration success unless the live integration was actually executed.

## Current implementation priority
Follow `docs/DEVELOPMENT.md`. The next priority is live Apify provider validation plus fixture normalization, then face runtime integration, then end-to-end orchestration.

## Change discipline
When a request conflicts with this file or an ADR, explain the conflict and propose the smallest architectural change needed. Do not silently make a breaking architectural decision.

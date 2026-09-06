# Security + Privacy Contract

## Biometric boundary

The input face is biometric data. Processing requires explicit user consent captured before face detection/embedding.

V1 should process the face locally and should not build a persistent biometric database.

Never write these to the blockchain:
- selfie bytes;
- face embeddings;
- biometric templates;
- face crops;
- private social content.

## Claim boundary

The system's claim is limited to:

> The supplied face representation is sufficiently similar to a face detected in the retrieved public media, under the configured model and threshold.

It is not a legal identity system and does not prove authorship, account ownership, consent, ownership of the image, or truthfulness of captions/content.

## Public social data boundary

Only public content that the selected provider can retrieve through its normal access path is eligible.

Do not:
- authenticate as the target user;
- use stolen/shared session cookies;
- access private accounts;
- bypass access controls;
- circumvent platform restrictions;
- aggressively evade rate limits.

## Untrusted URL boundary

Provider-returned URLs are attacker-controlled input.

`MediaFetcher` must enforce:

- HTTPS only;
- timeout;
- maximum body size;
- content-type allowlist;
- private/link-local/loopback IP blocking;
- no content execution;
- bounded redirect handling;
- safe temporary storage.

When hosted, DNS resolution and final connection IP must both be checked because DNS can change between validation and connection.

## Secrets

Keep secrets in environment variables/local secret storage. Never commit:

```text
.env
APIFY_API_TOKEN
wallet private keys
RPC credentials
```

The repository must contain `.env.example`, not a populated `.env`.

## Logging

Logs may include:
- platform;
- public post URL;
- provider run ID;
- structured failure code;
- timings;
- transaction hash.

Do not log:
- API tokens;
- wallet private keys;
- raw selfie bytes;
- raw face embeddings;
- unnecessary biometric-derived identifiers.

## Reproducibility

Evidence verification must depend on deterministic canonicalization and SHA-256 rather than a remembered UI state.

Provider output should be preserved as sanitized fixtures for development so normalization and orchestration can be tested without hitting live services on every run.

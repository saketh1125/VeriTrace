# ADR 0006: Apify behind a provider boundary

Status: Accepted

## Decision

Apify is an integration mechanism, not a core domain dependency. Input schemas and output normalization remain confined to `app/discovery`, while default Actor IDs are configured in `app/config/settings.py` and injected via `app/discovery/registry.py`.

## Consequence

An Actor can be replaced when it breaks, becomes paid, changes output, or a better official API becomes available without rewriting face matching, evidence, or blockchain code.

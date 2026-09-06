# ADR 0006: Apify behind a provider boundary

Status: Accepted

## Decision

Apify is an integration mechanism, not a core domain dependency. Actor IDs, input schemas and output normalization remain confined to `app/discovery`.

## Consequence

An Actor can be replaced when it breaks, becomes paid, changes output, or a better official API becomes available without rewriting face matching, evidence, or blockchain code.

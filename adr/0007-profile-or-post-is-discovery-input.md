# ADR 0007: User-directed social target is the primary discovery input

Status: Accepted

## Context

Global reverse-image search is unreliable as the critical path for this task. Generic image search can fail to return a known public social post even when the image is publicly accessible.

Platform-specific retrieval becomes much more deterministic when the user supplies a public post URL or a public profile/username. The provider can then perform its intended retrieval operation and return candidate URLs/media for our own verification layer.

## Decision

The primary discovery input is one of:

1. a public social post URL; or
2. a public profile/username.

The face model never performs web discovery. It verifies retrieved candidate media.

## Consequences

- The task becomes a bounded candidate-retrieval problem.
- Platform adapters can use official or community tooling without leaking provider-specific details into core logic.
- The product does not claim global internet discovery from a face alone.
- Reverse-image search remains an optional fallback.

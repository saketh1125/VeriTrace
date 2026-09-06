# ADR 0005: User-directed social discovery

Status: Accepted

## Decision

The primary discovery mechanism is a public social post URL or public profile target supplied by the user. Platform adapters enumerate candidate posts/media; local computer vision performs the actual face verification.

## Why

Global reverse-image search proved operationally unreliable for this use case. User-directed discovery turns the problem into a bounded retrieval task that platform-specific tooling is explicitly designed to support.

## Consequence

The product does not claim to find an unknown person's entire internet footprint from a face alone. Reverse-image search remains a fallback capability.

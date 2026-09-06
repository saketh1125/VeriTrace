# ADR 0008: Apify is an adapter implementation, not a domain dependency

Status: Accepted

## Decision

Apify Actors are called only from `app/discovery`. Their Actor IDs, request payloads, output field names, and normalization rules are isolated behind `SocialContentProvider`.

## Rationale

The selected Actors are community-maintained and can change availability, pricing, input schemas, output schemas, or behavior. The verification system must survive provider replacement.

## Consequences

- Provider integration tests must include fixtures from real Actor responses.
- Actor changes do not require changes to face matching, evidence hashing, or blockchain verification.
- An official platform API, another Actor, or a direct HTTP adapter may replace an Actor later without changing the domain contracts.

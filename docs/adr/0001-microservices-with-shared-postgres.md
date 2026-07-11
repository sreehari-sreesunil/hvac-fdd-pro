# ADR 0001: Microservices with a shared Postgres instance

## Status
Accepted

## Context
The platform is built as independently deployable microservices (auth, asset,
telemetry, ml, copilot, notification). True microservice practice often runs
one database instance per service.

## Decision
We run ONE Postgres container, but each service gets its own database within
it (auth_db, asset_db, telemetry_db, ...) and never queries another service's
database directly — only via that service's API. This keeps logical
service boundaries intact while avoiding the operational overhead of N
database containers for a small team.

## Consequences
- Easy to later split into separate DB instances per service if scale demands it —
  no application code change needed, just infra.
- Services must NOT share SQLAlchemy models or reach across database boundaries.
  Cross-service data access always goes through that service's HTTP API.

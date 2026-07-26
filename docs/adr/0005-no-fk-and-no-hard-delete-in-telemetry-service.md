# ADR 0005: No real foreign keys for cross-database references; EdgeDevice is never hard-deleted

## Status
Accepted

## Context
telemetry-service has two places where a naive design would reach for a
foreign key, and both turned out to be wrong for different reasons.

**TelemetryReading.metric_definition_id**: every reading is written the
moment it arrives, even if its `external_key` (e.g. "SAT", a raw BACnet
point name) can't yet be resolved to a known `MetricDefinition` —
ingestion must never drop data (see telemetry-service's core ingestion
design). `MetricDefinition` itself lives in asset-service's database
(`asset_db`), not telemetry-service's (`telemetry_db`) — per ADR-0001,
services never query another service's database directly, so a real
database-level foreign key across `telemetry_db` → `asset_db` is not
possible in the first place. Separately, once a reading is written, its
`metric_definition_id` is meant to be a permanent historical stamp of
what that reading was resolved to *at the time it was ingested* — later
remapping a `MetricMapping` must never retroactively rewrite readings
that were already resolved under a previous mapping.

**EdgeDevice → IngestionKey**: an `IngestionKey` is deliberately a
separate table from `EdgeDevice`, not columns on it, so a device can have
multiple keys over its lifetime (key rotation) — old keys get
`revoked_at` set rather than being deleted. If `EdgeDevice` were ever
hard-deleted with a `cascade="all, delete-orphan"` relationship to its
keys, that would silently destroy the audit trail needed to trace a
disputed sensor reading back to the credential that ingested it,
including keys that were already revoked before the device itself was
removed.

## Decision
`TelemetryReading.metric_definition_id` and `MetricMapping.metric_definition_id`
are logical references only (plain `String(36)` columns, no
`ForeignKey(...)`), matching the same "no cross-database FK" pattern
ADR-0001 already establishes for `Facility.organization_id`. A reading's
`metric_definition_id` is set once, at ingestion or backfill time, and is
never rewritten afterward, even if the corresponding `MetricMapping` is
later changed.

`EdgeDevice` rows are never hard-deleted — only soft-deleted via a
`deactivated_at` timestamp. The `EdgeDevice.ingestion_keys` relationship
intentionally has no `cascade="all, delete-orphan"`, so there is no code
path that can accidentally wipe a device's key history, including
already-revoked keys, as a side effect of removing the device.

## Consequences
- Nothing in telemetry-service can rely on the database itself to catch
  a `metric_definition_id` that points at a `MetricDefinition` which
  doesn't exist or was deleted in asset-service — that integrity has to
  be maintained by application logic (or accepted as a known gap), the
  same tradeoff ADR-0001 already accepts for other cross-service
  references.
- Historical readings stay accurate to what was known at ingestion time.
  Re-mapping an `external_key` to a different `MetricDefinition` later
  only affects new and still-unmapped readings (via the same backfill
  mechanism used when a mapping is first created) — it does not silently
  rewrite the past.
- "Deleting" a device in any future admin UI must mean setting
  `deactivated_at`, never a real `DELETE` — there is currently no
  endpoint that performs a hard delete, and none should be added without
  revisiting this decision first.
- Disputed or anomalous sensor data can always be traced back to the
  exact device and key that ingested it, even if that key has since been
  rotated out or the device itself has been deactivated.

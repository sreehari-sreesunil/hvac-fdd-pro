# ML Service Integration Notes

Running log for connecting the trained ML pipeline (ml/) to the real, running
backend services (auth-service, asset-service, telemetry-service). Parallel
in spirit to ml/MODEL_RESULTS_LOG.md, but for the integration/backend side.

## Milestone: first real end-to-end test succeeded

Real historical fault data (a 1200-row chunk of RTU_sim_condfouling50.csv) was
ingested through the ACTUAL running telemetry-service API (not a shortcut),
correctly mapped via the real metric-mapping mechanism, fetched back via the
real read API, assembled into a buffer, and scored by the real saved
`simulated_condenser_fouling` model - which correctly predicted fault=1 with
99.9% probability. This is the first proof that the EDA -> model -> saved
artifact -> live inference chain actually works against the real backend, not
just in isolated notebooks.

## Setup used for this test (ML Test Org)

- Org: "ML Test Org" (fresh signup, `mltest@example.com` - NOT the original
  test org from earlier backend sessions, whose credentials were lost)
- Facility: "ML Test Facility"
- Asset type: "RTU - Condenser Fouling Test" - 5 metric definitions, one per
  raw column condenser_fouling's model needs: `RTU_REFG_COND_PRES`,
  `RTU_REFG_COND_TEMP`, `RTU_TOT_CAPA`, `RTU_STG_STA`, `RTU_OA_TEMP`
- Asset: "ML-Test-RTU-01"
- Edge device + ingestion key generated and used to bulk-ingest real CSV data

**Scope, deliberately narrow**: only condenser fouling's 5 metrics were set
up, to prove the path end-to-end before expanding to the other 7 saved
models - same "start narrow, prove it, then scale" pattern used throughout
this project's EDA and modeling phases.

## Real gotchas discovered during this setup

1. **`POST /edge-devices` requires `facility_id` in the request body**, not
   just `asset_id` - not obvious from the field name alone, caught via a real
   `422` validation error, not assumed.
2. **Ingestion auth uses a custom header, `X-Ingestion-Key`** - not reflected
   in the OpenAPI spec's `security` field (FastAPI custom header dependencies
   often aren't registered as formal OpenAPI security schemes), so it had to
   be discovered by testing directly against the running API rather than
   trusted from the spec alone. `Authorization: Bearer` and `X-API-Key` were
   both tried first and correctly rejected before finding the right header.
3. **Access tokens expire in 30 minutes** (previously documented, re-confirmed
   here) - hit mid-session, surfaced as a confusing `403 "Not authorized for
   this facility"` on one endpoint before a `401 "Invalid or expired token"`
   on a different endpoint made the real cause clear. Different endpoints can
   surface an expired token as different error types depending on which
   check fails first - don't assume a 403 always means a real permissions
   problem.
4. **`GET /telemetry` sorts descending by `recorded_at`** (most recent
   first), and caps results at 500 rows - confirmed by testing, not assumed.
   A live buffer assembled from this endpoint must be re-sorted ascending
   before being handed to `live_features.py`, which expects ascending order.
5. **A single dummy test reading (used to figure out the ingestion auth
   header) is now permanently sitting in the system** with a 2026 timestamp,
   for the `RTU_TOT_CAPA` metric only. Harmless in practice - it doesn't
   align with any other metric's real 2018 timestamps, so an inner-join-based
   buffer assembly naturally excludes it - but it does mean `RTU_TOT_CAPA`'s
   own "most recent 500" window is offset by one row relative to the other
   4 metrics, which is why the assembled test buffer came out to 499 rows,
   not exactly 500. Not cleaned up (no delete-readings endpoint exists, per
   the documented API surface, and permanent deletion is generally avoided
   in this project) - just understood and accounted for.

## Standalone test scripts (not yet part of a real ml-service)

- `ingest_test_data.py` (repo root): bulk-ingests a CSV chunk into
  telemetry-service for a given asset, using stdlib only (`urllib`, `csv`,
  `json` - no new dependencies).
- `test_ml_pipeline.py` (repo root): fetches all of one model's required
  metrics back from telemetry-service, assembles a buffer, and runs
  `ml/src/models/inference.py`'s `predict()` - the actual proof-of-concept
  for the full chain. Requires a manually-pasted, current auth token (30-
  minute expiry) - NOT how a real `ml-service` should authenticate; this is
  a throwaway test script, not production code.

## Not yet done

- A real `ml-service` FastAPI microservice (this was all done via standalone
  scripts with a manually-pasted token - real service-to-service auth, e.g.
  an internal service account or API key, is not yet designed).
- Metric definitions/mappings for the other 7 saved models (only condenser
  fouling's 5 metrics exist so far).
- Any real-time/scheduled invocation - this was a one-shot manual test, not
  a running, periodic prediction loop.
- Writing predictions anywhere persistent (currently just printed to stdout).

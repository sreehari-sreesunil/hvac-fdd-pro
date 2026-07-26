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

## Milestone: the real ml-service (not a script) works end-to-end

Built a real FastAPI microservice at services/ml-service/, mirroring
telemetry-service's exact conventions (Poetry setup, pydantic-settings
config, verify_asset_access auth dependency reusing common.security). A
real GET /predictions/{asset_id}?model_name=... request against the actual
running service - not test_ml_pipeline.py's standalone script - correctly
authenticated, dynamically resolved metric names to real metric_definition_ids
via asset-service (no hardcoded mapping), fetched real telemetry, assembled
a live buffer, and returned a correct prediction (condenser fouling, 99.88%
fault probability, high confidence).

## Real gotcha discovered: docker-compose's JWT_SECRET_KEY does NOT come
## from services/*/.env files

`services/auth-service/.env` and `services/telemetry-service/.env` both
contain `JWT_SECRET_KEY=local-dev-secret-change-before-any-real-deployment-8f3k2`,
but the ACTUAL running Docker containers use
`dev-secret-change-me-in-production` - the fallback default baked into
docker-compose.yml's `${JWT_SECRET_KEY:-dev-secret-change-me-in-production}`
substitution. This substitution resolves against the host environment /
docker-compose's own env handling at compose-file-parse time, NOT by each
service loading its own local .env file inside the container.

Confirmed directly via `docker compose exec auth-service printenv
JWT_SECRET_KEY` - the only authoritative way to check, since two separate
.env files existing in the repo (both with a DIFFERENT value than what's
actually running) could easily mislead anyone reading them and assuming
they reflect real runtime configuration. ml-service's own .env was fixed
to use the real value. Worth flagging as a pre-existing, latent
inconsistency in this project's dev-environment setup - not something
introduced by this work, but only now surfaced because it directly broke
JWT verification during real testing.

## Milestone: fully containerized ml-service verified working

Added services/ml-service/Dockerfile (mirrors telemetry-service's exact
pattern) and a docker-compose.yml entry - ml/ mounted read-only at /ml
inside the container (models + src both accessible without rebuilding the
image on retrain), internal Docker network URLs for asset-service/
telemetry-service, and the correct docker-compose-substituted
JWT_SECRET_KEY (not the value from services/*/.env files - see the earlier
gotcha entry in this document).

Verified: the exact same prediction request that worked against the local
poetry-run dev server also works identically against the full containerized
stack (docker compose up -d) - same 99.88% fault probability result. This
is the first genuinely production-representative test of the whole system,
not just a local development shortcut.

Real operational note: `docker compose up -d --build <service>` appeared to
run in ATTACHED mode despite the -d flag in one test (logs streamed to the
terminal) - pressing Ctrl+C in that state stopped the entire stack, not
just the log view. If this happens again, use a plain `docker compose up
-d` (without --build) afterward, or open a separate terminal rather than
Ctrl+C-ing out of what might be an attached session.

## Real bug found and fixed: build_live_simulated_features assumed every
## model needs capacity smoothing

Setting up metric mappings for a comprehensive test asset (11 metrics, covering
all 8 saved models) and testing suction-line restriction (a capacity-EXCLUDED
model, per notebook 17's ablation-tested fix) immediately surfaced a real bug:
build_live_simulated_features unconditionally called add_segmented_ewma on
RTU_TOT_CAPA regardless of whether the model's feature_cols actually needed the
smoothed-capacity-residual feature. Models with include_capacity=False never
fetch raw capacity into their buffer (correctly, per required_raw_metrics) so
the unconditional smoothing step threw a KeyError the moment it ran against
such a model.

This never surfaced during the condenser_fouling test (our only test before
today), since that model DOES use capacity. Fixed by checking whether the
smoothed-capacity-residual feature is actually present in feature_cols
before attempting the computation at all - a direct, concrete justification for
testing a second, differently-configured model rather than assuming the pattern
generalizes from one success.

Verified after the fix: suction-line restriction correctly predicts fault=1 at
99.997 percent probability (matching this fault's extreme, EDA-established
effect sizes), with the model's real Usable with caveat status and exact
capacity-exclusion caveat text correctly surfaced in the response.

## New comprehensive test asset for testing remaining models

Created asset type RTU - Full Model Test (11 metric definitions, covering the
union of all 8 saved models' required_raw_metrics) and a new asset
ML-Test-RTU-Full (separate from the original condenser-fouling-only test
asset, to avoid risk of breaking the already-working setup). Ingesting each
remaining model's own fault-severity CSV and testing in turn is the repeatable,
proven next step - deliberately not done exhaustively for all 6 remaining
models in this same session (2 of 8 models now genuinely proven end-to-end,
covering both the capacity-included and capacity-excluded code paths).

# Load Testing

Basic load testing for ml-service's prediction endpoints, using
[Locust](https://locust.io/). Not a deployed service, not part of CI -
a developer tool, run ad hoc.

## Why ml-service, and why these endpoints

ml-service is the heaviest CPU/model-inference work in this platform
(real scikit-learn/XGBoost classifiers, SHAP explanation), making it
the most likely place to see real degradation under concurrent load -
unlike the other 5 services, which are comparatively thin CRUD/proxy
layers over Postgres.

`GET /predictions/{asset_id}/attribute` is the realistic heavy path -
it runs 4 real classifiers per request and is what copilot-service's
`diagnose_fault` tool actually calls when a user asks the copilot to
diagnose a fault. `GET /predictions/{asset_id}` (single classifier)
is tested alongside it to help distinguish whether any slowdown comes
from model-loading/inference overhead itself or from the argmax
endpoint's extra work.

## Setup

```bash
cd load-testing
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
pip install -r requirements.txt
```

## Prerequisites

The real stack must be running (`docker compose up -d`), and the real
test asset/data must exist (`ML-Test-RTU-Full`, seeded via
`ingest_test_data.py` at the repo root - see that script if the asset
doesn't exist yet).

## Running

```bash
locust -f locustfile.py --host http://localhost:8003
```

Then open `http://localhost:8089` in a browser, set the number of
simulated users and spawn rate, and start the run. Locust's own web UI
shows live response-time percentiles, request rate, and failure rate;
a CSV/HTML report can be exported from there for saving real evidence
of a given run (`docs/LOAD_TEST_RESULTS.md` documents specific runs
and findings).

## What "basic" means here

This is a starting point, not a comprehensive load-testing suite:

- Only exercises ml-service's two prediction endpoints, not the other
  5 services.
- Uses one real, seeded test asset (`ML-Test-RTU-Full`), not a
  variety of assets/orgs - a real production load pattern would spread
  requests across many different assets/facilities, which this doesn't
  simulate.
- Single-machine load generation (Locust running locally) - a genuine
  high-scale test would run distributed load generators.
- No sustained soak-testing (memory leaks, connection-pool exhaustion
  over hours) - only short-duration runs so far.

Worth expanding later if real usage patterns or a real incident
suggest it's needed; not over-built preemptively, matching this
project's stated "no unnecessary heavy infrastructure" philosophy.

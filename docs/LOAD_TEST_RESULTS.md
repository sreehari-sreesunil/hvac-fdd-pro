# Load Test Results

Real, evidence-based findings from basic load testing against
ml-service, using the tool in `load-testing/`. This document records
what was actually measured and what conclusions the evidence supports
- including one finding that was investigated but not fully root-caused,
recorded honestly rather than left out or overclaimed.

## Setup

- Tool: Locust (see `load-testing/README.md` for why)
- Target: ml-service's two prediction endpoints, weighted 3:1 toward
  `GET /predictions/{asset_id}/attribute` (the heavier, real-world path)
- Test data: the real seeded `ML-Test-RTU-Full` asset, same one used
  throughout this project's live verification
- Load level: 10 simulated users, spawn rate 2/s, 1-3s wait between a
  user's requests

## Finding 1: a real bug - blocking calls on the event loop

**What we found.** The first test run showed 9 of 14 login attempts
failing. Investigation (reproducing with a rapid `curl` loop) confirmed
this was auth-service's real, working 5/minute login rate limit
correctly doing its job - not a bug, but a test-design flaw:
simulated users all logging in within a few seconds of each other from
one IP mostly got rate-limited before ever reaching ml-service. Fixed
by having the test log in once and share the token across all
simulated users (matching how the real frontend authenticates once and
reuses the token via refresh-on-401), which cleanly isolates ml-service
as the actual system under test.

**What we found next.** With login fixed, requests reached ml-service
cleanly (0 failures), but `/attribute`'s median response time was
**11 seconds** under just 10 concurrent users - a single, non-concurrent
call to the same endpoint takes about 2 seconds. Inspecting
`app/routers/predictions.py` confirmed `load_model()`, `predict()`, and
`explain()` - all synchronous, CPU-bound (real joblib deserialization,
real scikit-learn/XGBoost inference) - were called directly inside
`async def` route handlers. Python's asyncio event loop is
single-threaded: a synchronous call inside it blocks the *entire* loop
for its full duration, meaning every other concurrent request - even
an unrelated `/health` check - has to wait.

**Fix.** Wrapped both call sites in FastAPI's `run_in_threadpool()`
(commit `e0fa97f`), so blocking model work runs off the event loop.
This also exposed a related, previously-harmless race: the in-process
model cache's check-then-load-then-set pattern had no lock, which
never mattered when `predict()` ran serially on the event loop but
could now cause redundant (not corrupting) concurrent loads once
`load_model()` genuinely runs across threads. Added a plain
`threading.Lock` - same commit.

**Verification.** 20/20 ml-service tests + 6/6 `ml/` tests passing,
`mypy` clean on both, via the real Docker environment for ml-service
and a direct local `poetry run` for `ml/`.

This fix is correct and worth keeping on its own merits regardless of
Finding 2 below - it genuinely frees the event loop to keep serving
other concurrent requests while a model prediction is in flight, which
matters for this service's overall responsiveness even if it turned
out not to be the dominant cause of this specific test's latency.

## Finding 2: the fix didn't reduce the measured latency - honestly unresolved

**What we expected.** With blocking calls now offloaded, we expected
`/attribute`'s median response time under the same 10-user load to
drop meaningfully.

**What we measured.** It didn't. A second run under identical
conditions still showed an ~11 second median, effectively unchanged.

**What we ruled out.** `docker stats` watched live during a fresh run
showed ml-service's CPU usage at 0.16-0.21% throughout - essentially
idle. This rules out CPU-bound contention *within ml-service itself*
(e.g. multiple concurrent model predictions competing for CPU cores)
as the cause.

**What we didn't fully verify, but is the leading hypothesis.**
`build_buffer()` (`app/services/buffer_builder.py`) makes one call to
asset-service plus one *sequential* call to telemetry-service per
required raw metric, and this whole sequence repeats once per model -
roughly 12-16 sequential cross-service HTTP calls for a single
`/attribute` request. telemetry-service's own routes (confirmed via
grep of `app/routers/telemetry.py`) have the same
synchronous-call-inside-`async def` pattern ml-service just got fixed
for, though the per-call blocking duration there (a Postgres query) is
typically much shorter than a full model prediction. Under concurrent
load, if telemetry-service or asset-service end up serializing *their
own* handling of many simultaneous incoming requests from ml-service,
that would show up as exactly this kind of latency growth without
ml-service's own CPU being touched at all - but this was not directly
measured (we did not capture live `docker stats` for telemetry-service
or asset-service during a run, and did not instrument the individual
cross-service call latencies to confirm where time is actually being
spent).

**Decision: stopped here, deliberately.** Chasing the exact mechanism
further - instrumenting individual call latencies, watching all
services' CPU simultaneously, testing whether the same synchronous-DB
pattern exists and matters in telemetry-service/asset-service - is
real, valuable work, but it's genuine performance engineering, not
"basic load testing." Recorded here as a concrete, scoped follow-up
rather than either quietly abandoned or falsely presented as resolved.

## Open follow-up (not started)

- Instrument or directly measure telemetry-service/asset-service CPU
  and per-call latency during a concurrent ml-service load test, to
  confirm or rule out downstream service contention as the actual
  bottleneck.
- `build_buffer()`'s per-metric telemetry fetches are sequential
  (`for metric_name in required_raw_metrics: await fetch_metric_readings(...)`),
  not run concurrently via `asyncio.gather()` - worth testing whether
  parallelizing these reduces latency independent of any other finding
  above, since it's a real, inherent sequential-work cost per request
  regardless of what's causing the load-test-specific slowdown.
- `app/routers/baselines.py` has the same
  synchronous-call-inside-`async def` pattern (`LinearRegression.fit()`/
  `.predict()`) as the one fixed in this document's Finding 1, but on a
  much lighter workload with no test evidence it's currently a real
  problem - noted, not fixed, since fixing something without evidence
  it's broken isn't real engineering judgment, just applying the same
  pattern reflexively.
- The same synchronous-`db.query()`-inside-`async def` pattern exists
  across telemetry-service's routes (and likely every other service,
  given the shared classic-SQLAlchemy convention) - not fixed here,
  since a typical Postgres query's blocking duration is small relative
  to ml-service's model-inference case, but worth a dedicated audit if
  the follow-up investigation above confirms it's a real contributor.

## Commits

- `4e5798c` - load-testing tool added
- `e0fa97f` - the real fix (thread-pool offload + cache lock)

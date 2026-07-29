# Per-Asset Rolling Baseline: Validation Log

## Purpose

Distinct from both the fault classifiers (fixed signatures for known fault
types) and the anomaly gatekeeper (population-level "abnormal in general,
across many assets"): this asks "does THIS SPECIFIC unit deviate from ITS
OWN history?" It's meant to catch real unit-to-unit variation and novel
failure modes the other two mechanisms structurally can't - a classifier
can only recognize faults it was trained on, and the gatekeeper's notion
of "normal" is pooled across the whole fleet, not tuned to one asset's
particular installation, ducting, or equipment quirks.

## Attempt 1: Continuously-recalculating rolling window

WINDOW=60 rows, K_STD=3.0, mean/std recalculated at every row from the
trailing window. Result: FAILED - flat ~1% deviation rate at every fault
severity tested (10% through 50%), no gradient at all.

Root cause: each fault CSV is fixed-severity from row 1 (the whole file
is fault-affected, not just part of it - see "Attempt 4 addendum" below,
however, for a caveat about *which* rows actually count). A short rolling
window "forgets" the true pre-fault baseline within about an hour of
entering fault-affected data, since the window itself fills up with
fault-affected readings and treats them as normal.

## Attempt 2: Concatenate baseline + fault (baseline first)

Same rolling-window mechanism, but feed baseline.csv first, then the
fault file, so the window starts genuinely clean. Result: STILL FAILED,
same flat ~1% result. The window is far too short relative to the
fault-portion length to retain any memory of the earlier clean period by
the time it's deep into fault data.

## Attempt 3: Frozen baseline (raw pressure)

Compute mean/std ONCE from a reference period, never recalculate.
Implemented as `FrozenBaseline` in `ml/src/features/rolling_baseline.py`.
Tested on raw `RTU_REFG_COND_PRES` (no weather adjustment). Result:
WORKED, but weak - baseline deviation rate 1.05%, condenser fouling
climbed 1.46% (10% severity) -> 30.33% (50% severity). A real, monotonic
gradient, but a weak one - even severe fouling only breached 3-sigma
about a third of the time.

## Critical catch: raw pressure vs. weather-residualized

Every other model in this project (all classifiers, the anomaly
gatekeeper) residualizes physical signals against outdoor air temperature
before doing anything else, because `RTU_OA_TEMP` explains 77-99% of
several features' baseline-condition variance (see
`ml/src/features/build_features.py`'s module docstring) - variance
comparable in magnitude to some faults' true effect size. The Attempt-3
validation used raw pressure directly, inconsistent with that established
discipline. Re-validated using `ml/src/features/build_features.py`'s
weather-residualized `RTU_REFG_COND_PRES_residual` instead:

| Severity | Raw pressure (Attempt 3) | Weather-residualized |
|---|---|---|
| Baseline itself | 1.05% | **0.29%** |
| 10% | 1.46% | **36.75%** |
| 20% | 2.07% | **99.20%** |
| 30% | 4.20% | **99.93%** |
| 40% | 13.95% | **99.87%** |
| 50% | 30.33% | **100.00%** |

The raw-pressure version wasn't just weaker - it badly understated a much
stronger real signal, because weather variance was drowning out the true
fault effect. Confirmed: this mechanism must operate on
weather-residualized values, matching every other model in the project.

## Final design

`ml/src/features/rolling_baseline.py`: `FrozenBaseline` dataclass
(mean, std, n_reference_rows) with `.z_scores()` / `.flag_deviations()`
methods, `fit_frozen_baseline(reference_series)` factory function. Module
is agnostic to *how* the series was residualized - that logic lives in
the caller (offline: `build_feature_table`; live:
`services/ml-service/app/routers/baselines.py`, a lightweight two-column
`LinearRegression(weather -> target)` fit, since a single-metric baseline
doesn't need the full pipeline's EWMA smoothing, which is specific to the
`RTU_TOT_CAPA` capacity column).

"Adaptive" was reframed during this work as PER-ASSET personalization -
each asset gets its own frozen reference fit from its own history - not
continuous recalculation, which Attempts 1-2 showed doesn't work for this
data shape.

## Persistence: `asset_baselines` table

New table in a new `ml_service_db` database (ml-service's first-ever
database - previously stateless). Columns: `mean`, `std` (of the
residual), `weather_col`, `weather_slope`, `weather_intercept` (fit once
from the reference period, applied - never refit - at serving time,
matching the exact discipline every classifier/gatekeeper already
follows for the same reason: live data has no way to know which readings
are "baseline" to refit against), `n_reference_rows`, `fit_at`. Two
Alembic migrations: `a50f8bea32d8` (base table), `3317f58cec87` (added
the three weather-residualization columns after the raw-vs-residualized
finding above required them).

`POST /baselines/{asset_id}?metric_definition_id=...` fits (or
deliberately re-fits - re-fitting fully replaces the stored row, not an
average) a baseline from whatever telemetry is currently available.
`GET /baselines/{asset_id}?metric_definition_id=...&k_std=3.0` scores the
latest reading against the stored baseline.

KNOWN LIMITATION: capped at telemetry-service's `GET /telemetry` 500-row
limit, so the reference period achievable today is short. A genuine
commissioning-period baseline (days/weeks of trusted history) would need
that endpoint's pagination extended first - flagged as real, deliberate
follow-up work, not solved here.

## Bug caught during live end-to-end testing: missing stage-2 filter

The first live test (fit against whatever was already ingested, score
against freshly-ingested `condfouling40` data) gave a misleadingly weak
result (`z_score` barely moved, ~1.06 -> ~1.07) that looked like the
mechanism didn't work at all. Root-caused via a real diagnostic process,
not assumption:

1. First suspicion (timestamp divergence between the target metric and
   `RTU_OA_TEMP`, the exact bug class hit during Phase A2) - checked
   directly, ruled out. Both metrics' windows were correctly aligned.
2. Second suspicion (identical weather values across two different fault
   ingestions looked like stale data) - investigated and found to be
   expected, not a bug: these simulated fault CSVs share the same
   underlying weather trace at a given row index, since faults don't
   change outdoor air temperature.
3. Actual root cause: **the very first live fit was accidentally
   performed against `evapfouling40` data** (whatever happened to be
   already ingested from earlier ML validation work), not genuine
   fault-free `baseline.csv` data - comparing one fault against another,
   not against clean baseline.
4. After correcting that (re-ingesting genuine `baseline.csv`, re-fitting
   against it), the live score against fresh `condfouling40` data was
   STILL weak. Investigation of `build_feature_table` revealed it calls
   `stage2_only()` (`ml/src/features/filtering.py`), filtering to
   `RTU_STG_STA > 0.9` before any residualization - a filter the live
   `baselines.py` router had never implemented. Direct check confirmed
   the live test's ingested row window was only 43.7% stage-2 (the rest
   off or stage-1); the router's "latest reading" could easily have
   landed on a non-stage-2 point, comparing noise, not signal, against a
   fit built from a similarly-unfiltered reference.

Fixed by adding the identical `RTU_STG_STA > 0.9` filter to
`_fetch_target_and_weather()` in `baselines.py`, applied to BOTH fitting
and scoring, matching `build_feature_table`'s exact threshold and
reasoning.

## Final live verification (after the stage-2 fix)

Fit against genuine, stage-2-filtered `baseline.csv` data:
`n_reference_rows=202` (out of the 500 available - confirms filtering is
active), `std=175,377` (down from ~2.6M unfiltered - a much tighter,
cleaner reference distribution).

Scored against freshly-ingested `condfouling40` data, without re-fitting:
**`z_score=18.09`, `is_deviation=true`** - a strong, decisive result, far
past the `k_std=3.0` threshold, consistent with the offline validation's
99.87% detection rate at this severity.

## Status

Design validated, both offline and live end-to-end, with a real bug
caught and fixed during live testing rather than papered over. Not yet
covered: automated tests for the new endpoints (Phase B3 scope), and the
500-row reference-period limitation above.

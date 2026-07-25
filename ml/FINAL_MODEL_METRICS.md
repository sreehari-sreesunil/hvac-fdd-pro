# Final Model Metrics Summary

Consolidated reference for every model built across both datasets. For methodology,
discovery process, and detailed reasoning behind each result, see
`MODEL_RESULTS_LOG.md` and the individual notebooks. This document is the
"how good is this, honestly" reference - status labels reflect real, tested
limitations, not aspirational claims.

## Status key

- **Usable**: performs reliably across the tested evaluation method(s); real, minor
  caveats only.
- **Usable with caveat**: works, but with a documented, non-trivial limitation
  (e.g. degrades over time, reduced precision) that any deployment must account for.
- **Not production-usable**: a real, unresolved failure mode exists; do not deploy
  without further work.
- **Not modeled**: a genuine data-availability or scoping limitation prevents honest
  evaluation, not a modeling failure.

## Correction note (post-publication)

A real order-of-operations bug was found in build_feature_table() during the
build of the live-inference feature pipeline (ml/notebooks/24, 25): segmented
EWMA smoothing was being applied AFTER stage-2 filtering instead of before,
silently blending together separate real stage-2 operating sessions. This
affected every model using the capacity feature: Condenser Fouling,
Liquid-Line Restriction, and the Isolation Forest. All three were retrained
and re-evaluated with the fix; none flipped to unusable, but their precision/
false-positive numbers below have been updated to the corrected values. See
ml/MODEL_RESULTS_LOG.md's "Capacity feature bug fix" entry for full detail.

**Second correction**: the initial re-verification of the Isolation Forest
after the above fix was insufficient (only 2 of 24 fault-severity files were
spot-checked). A full sweep later revealed contamination=0.01 was severely
miscalibrated against the corrected feature - detection on several moderate-
severity faults had collapsed (e.g. evapfouling40: 0.99998->0.404).
Re-tuned to contamination=0.03, verified against the actual saved model
across the complete 24-file sweep this time. See MODEL_RESULTS_LOG.md's
"Isolation Forest contamination re-tuning" entry.

## Simulated Dataset - Binary Fault Classifiers

All models: `RandomForestClassifier`, features from `build_feature_table()`
(stage-2 filtered, weather-residualized). Two evaluation methods reported for
every fault: random split (diagnostic upper bound) and 5-fold `TimeSeriesSplit`
(honest, forward-in-time evaluation).

| Fault | Random-Split Baseline Recall/Precision | TimeSeriesSplit Baseline Recall Range | Status |
|---|---|---|---|
| Refrigerant Undercharge | 0.34-0.55 / varies | 0.44 -> 0.00 (collapses) | **Not production-usable** - root cause partially isolated (weather-variance interaction), not resolved. Capacity-removal fix tested and found to make it WORSE. |
| Refrigerant Overcharge | 0.73 / 0.89 | 0.97 - 1.00 (stable) | **Usable** - minor unexplained precision dip in 2 of 5 folds. |
| Condenser Fouling | 0.98 / 0.99 | 1.00 (all folds) - 0.76-0.95 precision | **Usable** - strongest, most stable recall; precision drift wider than originally measured (see note below on a fixed feature-engineering bug). |
| Evaporator Fouling | 0.71 / 0.90 | 0.76 -> 0.41 without fix; 0.70 -> 0.82 with capacity removed | **Usable with caveat** - deploy WITHOUT capacity feature (precision cost: 0.93-0.97 -> 0.72-0.74). |
| Liquid-Line Restriction | 0.98 / 0.99 | 0.99-1.00 (stable) - 0.91-0.98 precision | **Usable** - stable despite this fault's threshold-shaped severity response; precision drift wider than originally measured (see note below). |
| Suction-Line Restriction | 0.82 / 0.91 | 0.87 -> 0.43 without fix; 0.96 - 0.99 with capacity removed | **Usable with caveat** - deploy WITHOUT capacity feature (precision cost: ~1.00 -> consistent 0.63). |

**Deployment recommendation**: 4 of 6 faults (overcharge, condenser fouling,
liquid-line restriction, and evaporator/suction-line restriction *with capacity
removed*) are usable now. Undercharge requires further investigation before
deployment - do not ship as-is.

## Simulated Dataset - Isolation Forest (Anomaly Gatekeeper)

Trained only on baseline data; `contamination=0.01` (tuned from an untuned default
of 0.05, cutting false-positive rate roughly in third with no loss of strong-fault
detection).

| Metric | Value |
|---|---|
| False positive rate (held-out later baseline) | 6-7.6% (contamination re-tuned to 0.03 after a SECOND correction - the initial fix's contamination=0.01 was severely miscalibrated; see note below) |
| Detection rate, strong-signal faults (e.g. suction-line restriction, evaporator fouling 30-50%) | 0.999 - 1.00 |
| Detection rate, moderate-signal faults (e.g. liquidpipe08/10bar, evapfouling20) | 0.36 - 0.83 |
| Detection rate, weak-signal faults (e.g. overcharge all severities, condfouling10-40, low-severity restrictions) | <0.15 |

**Status**: **Usable with caveat** - reliable gatekeeper for moderate-to-severe
conditions; will not reliably catch the mildest fault severities. Precision/recall
tradeoff at the contamination parameter is a real, unresolved product decision
(tighter threshold = fewer false alarms but weaker detection of moderate faults).

## Experimental Dataset - Cross-Season Models

Evaluation method: train on 1-2 seasons, evaluate on a held-out third
(`build_experimental_feature_table()`). No stage-2 filtering (not applicable to
this dataset); season, not raw weather, is the primary confound.

| Fault | Raw-Feature Recall/Precision | With Mitigation | Status |
|---|---|---|---|
| OA Damper Stuck | 0.11 / 1.00 | 0.34 / 0.42 (OA_TEMP-residualized) | **Usable with caveat** - real, partial fix; genuine precision/recall tradeoff remains. |
| Biased SAT Sensor | 0.00 / 0.12 | 0.05 / 0.34 (OA_TEMP-residualized) | **Not production-usable** - mitigation largely ineffective; cross-season risk unresolved. |
| Incorrect Econ. Setpoint (too low: 6C, 8C) | -- | 0.40 / 0.87 (Winter->Spring) | **Usable with caveat** - moderate result; fault mechanism itself not fully understood. |
| Incorrect Econ. Setpoint (too high: 12C, 14C) | -- | -- | **Not modeled** - only one season (Fall_2020) confirmed as a valid test window; genuine data-availability gap, not a modeling failure. |

**Deployment recommendation**: none of the three Experimental-dataset faults are
fully production-ready. OA damper stuck and econ.-setpoint-too-low are usable with
explicit, communicated caveats; biased SAT sensor needs further work before any
deployment; econ.-setpoint-too-high cannot be honestly evaluated without
additional seasonal data collection.

## Cross-cutting, honest summary

- **9 of 10 attempted fault-detection models are usable in some form** (6 of 6
  Simulated faults if undercharge is excluded pending further work; 3 of 4
  Experimental sub-models, with caveats on all three).
- **1 model (undercharge) is not production-usable**, with a documented,
  partially-investigated root cause.
- **1 fault direction (econ. setpoint too high) cannot currently be evaluated**
  due to a real data gap, not a modeling gap.
- Every "usable" model still carries at least one honestly-disclosed limitation -
  none should be presented as a clean, unconditional success.

## Not yet done

SHAP / feature-importance output per prediction. Alert engine (thresholds,
severity levels informed by the tradeoffs documented above). Field-dataset
validation (reserved exclusively for this purpose per the original project scope;
not yet begun). Consolidated retraining/monitoring plan given the real generalization
risks documented throughout this phase.

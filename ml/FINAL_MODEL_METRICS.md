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

All models: `RandomForestClassifier`, EXCEPT evaporator fouling, which uses
`XGBClassifier` as of a multi-algorithm comparison (see `MODEL_COMPARISON_LOG.md`
for full methodology and per-fault rationale). Features from `build_feature_table()`
(stage-2 filtered, weather-residualized). Two evaluation methods reported for
every fault: random split (diagnostic upper bound) and 5-fold `TimeSeriesSplit`
(honest, forward-in-time evaluation) - except evaporator fouling's current entry,
which reports only TimeSeriesSplit (random-split is optional diagnostic-only per
MODEL_ACCEPTANCE_CRITERIA.md and was not computed in the comparison harness).

| Fault | Random-Split Baseline Recall/Precision | TimeSeriesSplit Baseline Recall Range | Status |
|---|---|---|---|
| Refrigerant Undercharge | 0.34-0.55 / varies | 0.44 -> 0.00 (collapses) | **Not production-usable** - root cause partially isolated (weather-variance interaction), not resolved. Capacity-removal fix tested and found to make it WORSE. |
| Refrigerant Overcharge | 0.73 / 0.89 | 0.97 - 1.00 (stable) | **Usable** - minor unexplained precision dip in 2 of 5 folds. |
| Condenser Fouling | 0.98 / 0.99 | 1.00 (all folds) - 0.76-0.95 precision | **Usable** - strongest, most stable recall; precision drift wider than originally measured (see note below on a fixed feature-engineering bug). |
| Evaporator Fouling | N/A - not computed for XGBoost, see note above | 0.949-0.952 recall / 0.967-0.970 precision (XGBoost, capacity excluded) | **Usable** - SWITCHED from Random Forest (which had a 0.76->0.41 recall floor) to XGBoost per `MODEL_COMPARISON_LOG.md`; stable across all 5 folds. Superseded row, kept below for history: RF/0.71-0.90/0.76->0.41 without fix, 0.70->0.82 with capacity removed/was "Usable with caveat". |
| Liquid-Line Restriction | 0.98 / 0.99 | 0.99-1.00 (stable) - 0.91-0.98 precision | **Usable** - stable despite this fault's threshold-shaped severity response; precision drift wider than originally measured (see note below). |
| Suction-Line Restriction | 0.82 / 0.91 | 0.87 -> 0.43 without fix; 0.96 - 0.99 with capacity removed | **Usable with caveat** - deploy WITHOUT capacity feature (precision cost: ~1.00 -> consistent 0.63). |

**Deployment recommendation**: 5 of 6 faults (overcharge, condenser fouling,
evaporator fouling, and liquid-line restriction as full "Usable"; suction-line
restriction as "Usable with caveat", deployed *with capacity removed*) are usable
now. Undercharge requires further investigation before deployment - do not ship
as-is.

## Simulated Dataset - Anomaly Gatekeeper (One-Class SVM)

SWITCHED from Isolation Forest to One-Class SVM per
ANOMALY_DETECTOR_COMPARISON_LOG.md - a multi-algorithm comparison triggered by
external review feedback. Trained only on baseline data; `nu=0.01`, `kernel=rbf`.

| Metric | Value |
|---|---|
| False positive rate (held-out later baseline) | 2.95% - lower than Isolation Forest's best achievable 2.87% at its own most conservative setting, and far below its shipped 7.6% (contamination=0.03) |
| Detection rate, strong-signal faults (e.g. suction-line restriction, evaporator fouling 40-50%) | 1.00 |
| Detection rate, moderate-signal faults (e.g. liquidpipe10bar, evapfouling30) | 0.76 - 0.98 |
| Detection rate, weak-signal faults (e.g. overcharge all severities, condfouling all severities) | <0.10 |

**Status**: **Usable** (upgraded from "Usable with caveat") - at a near-identical
FPR to Isolation Forest's best setting, detects evapfouling30 98.4% of the time
versus Isolation Forest's 13.5% - a different tier of gatekeeper performance, not
a marginal gain. Local Outlier Factor was also compared and showed comparable
detection but was disqualified on deployment grounds (11.9MB serialized model
embedding the full training set, vs. SVM's 24.6KB). Full comparison methodology,
every algorithm/hyperparameter tested, and the real bug found and fixed in the
comparison harness itself (an FPR-only selection rule has a trivial optimum and
would have reproduced Isolation Forest's own known contamination=0.01 detection
collapse) are documented in ANOMALY_DETECTOR_COMPARISON_LOG.md.

**Historical note**: the original Isolation Forest's `contamination` re-tuning
(0.01 -> 0.03 after a capacity-feature bug fix, detailed in the previous version
of this section and in MODEL_RESULTS_LOG.md) remains a real, valuable record of
this project's evaluation discipline - preserved in git history and
MODEL_RESULTS_LOG.md, not deleted, even though Isolation Forest itself is no
longer deployed.

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

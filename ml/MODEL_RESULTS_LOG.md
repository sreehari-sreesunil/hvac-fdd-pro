# Model Results Log (Simulated Dataset, One-vs-Rest Binary Classifiers)

Running log, updated after each fault is modeled. Architecture decision: one binary
classifier per fault (not a single multi-class model), since each fault needs
different, EDA-informed features per the cross-fault EDA summary. All models use
`build_feature_table()` (`ml/src/features/build_features.py`) - stage-2 filtering,
segmented EWMA smoothing, and weather-residualization applied uniformly, with
per-fault feature column choices informed by that fault's own EDA notebook.

**Standing evaluation practice**: report both a random train/test split (a diagnostic
upper bound, not representative of real deployment) and 5-fold `TimeSeriesSplit`
(the honest, forward-in-time evaluation) for every fault - never rely on random-split
metrics alone.

## Undercharge (notebook 11)
- **Features**: suction pressure/temp, discharge pressure, capacity (all
  weather-residualized).
- **Random split**: reasonable (~34-81%, varies by model attempt).
- **TimeSeriesSplit**: collapses, fold 1 (0.44) -> fold 5 (0.00).
- **Root cause**: weather-driven variance in baseline is comparable in magnitude to
  the fault effect; residualizing helps near-term folds but not far-future ones.
  Genuinely unresolved.
- **Status**: NOT production-usable as-is.

## Overcharge (notebook 12)
- **Features**: suction pressure/temp, discharge pressure (capacity excluded - not
  established as a strong signal for this fault).
- **Random split**: baseline recall 0.73, precision 0.89.
- **TimeSeriesSplit**: baseline recall 0.97-1.00, stable, no degradation.
- **Status**: genuinely usable, minor unexplained precision dip in folds 1 and 5.

## Condenser fouling (notebook 13)
- **Features**: condenser pressure/temp, capacity.
- **Random split**: baseline recall 0.98, precision 0.99.
- **TimeSeriesSplit**: baseline recall 0.99-1.00, stable.
- **Status**: strongest, most stable of the six.

## Evaporator fouling (notebook 14)
- **Features**: suction pressure/temp, supply air temp, capacity - the dataset's
  strongest capacity signal (Cohen's d=1.376).
- **Random split**: baseline recall 0.71, precision 0.90.
- **TimeSeriesSplit**: degrades gradually, 0.76 -> 0.41, plateaus (does not collapse
  to zero). Precision stays high (0.93-0.97) throughout.
- **Status**: usable, with a real, honestly-reported degradation caveat.

## Liquid-line restriction (notebook 15)
- **Features**: suction pressure/temp, discharge pressure, capacity. Genuine
  threshold-shaped severity response (minimal effect at 1-4 bar, sharp jump at
  8-10 bar) per notebook 05's EDA.
- **Random split**: baseline recall 0.98, precision 0.99.
- **TimeSeriesSplit**: baseline recall 0.99-1.00, stable - despite the threshold
  shape, ruling out severity shape as an explanation for stability.
- **Status**: stable, near-perfect.

## Suction-line restriction (notebook 16)
- **Features**: suction pressure/temp, capacity - the dataset's single strongest,
  cleanest effect sizes overall (Cohen's d=4.439 at even the mildest severity gap).
- **Random split**: baseline recall 0.82, precision 0.91.
- **TimeSeriesSplit**: degrades, 0.87 -> 0.43, matching evaporator fouling's
  pattern. Precision stays near-perfect (0.99-1.00) throughout.
- **Key finding**: the single strongest signal in the whole dataset STILL degrades
  forward-in-time - conclusively rules out signal strength as the explanation for
  stability.
- **Status**: usable, with the same real degradation caveat as evaporator fouling.

## Cross-fault pattern: all 6 Simulated faults modeled, capacity-magnitude
hypothesis tested directly (notebook 17)

| Fault | Random split baseline recall | TS fold range (baseline recall) | Pattern |
|---|---|---|---|
| Undercharge | ~0.34-0.55 | 0.44 -> 0.00 | Collapses |
| Overcharge | 0.73 | 0.97 - 1.00 | Stable |
| Condenser fouling | 0.98 | 0.99 - 1.00 | Stable |
| Evaporator fouling | 0.71 | 0.76 -> 0.41 | Gradual decline |
| Liquid-line restriction | 0.98 | 0.99 - 1.00 | Stable |
| Suction-line restriction | 0.82 | 0.87 -> 0.43 | Gradual decline |

**Initial correlational observation** (before direct testing): the three degrading/
collapsing faults all had large-magnitude capacity swings as a major effect; the
three stable faults did not. This suggested a single, uniform "capacity causes
degradation" rule.

**Directly tested in notebook 17** by removing capacity from each degrading fault's
feature set and re-running TimeSeriesSplit. Result: **the hypothesis is TRUE for 2
of 3 faults, FALSE for the third**:

- **Evaporator fouling**: CONFIRMED. Without capacity, the degradation trend
  reverses to improvement (0.76->0.41 becomes 0.70->0.82). Real precision cost
  (0.93-0.97 -> 0.72-0.74).
- **Suction-line restriction**: CONFIRMED, dramatically. Without capacity, recall
  becomes stable and near-perfect (0.87->0.43 becomes 0.96-0.99 stable). Real
  precision cost (~1.00 -> consistent 0.63).
- **Undercharge**: FALSIFIED. Without capacity, EVERY fold got worse, not better
  (fold 1: 0.44 -> 0.12). Capacity is undercharge's most helpful feature, not its
  problem - its instability has a genuinely different, still-unknown cause.

**Conclusion**: this is a real, useful, but partial explanation, not a universal
rule. For 2 of 3 degrading faults, dropping capacity is a concrete, tested fix that
trades precision for much more reliable forward-in-time behavior - recommended for
real deployment of evaporator fouling and suction-line restriction detectors.
Undercharge's instability remains genuinely unresolved and should NOT be assumed to
share the same cause or fix - flagged as a standing open item, not chased further
per this project's proportionality standard (already invested two full debugging
sessions into it in notebook 11 without full resolution).

## Isolation Forest anomaly detector (notebook 18)

**Architecture role**: the "gatekeeper" model in the two-model architecture -
trained ONLY on baseline data, no fault labels used during training. Answers "does
this look abnormal at all," distinct from the binary classifiers' "which specific
fault is this."

**Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, capacity (weather-
residualized) - deliberately narrow and general-purpose, not the union of every
fault's specialized features.

**Tuning**: bounded check of 3 contamination values (0.01, 0.05, 0.10). Adopted
contamination=0.01 - meaningfully lower false-positive rate (6.1% vs 16.1% at the
untried default 0.05) with no loss of strong-fault detection (100% either way).

**Final results (contamination=0.01)**:
- False positive rate on held-out later baseline: 6.1% - still above the nominal 1%
  calibration target, echoing the same forward-in-time drift theme seen across
  several binary classifiers, but a real, tuned improvement over the untuned default.
- Detection rate forms an honest gradient closely matching EDA effect sizes:
  near-perfect (>0.99) for suction-line restriction and evaporator fouling 30-50%;
  moderate (0.42-0.81) for liquidpipe08/10bar and evapfouling20; weak (<0.25) for
  everything the EDA already flagged as low-severity or weak-signal (overcharge at
  every severity, condfouling10-40, undercharge10/15, liquidpipe01/04bar).

**Real, unresolved tradeoff**: tightening the threshold to cut false positives also
cut detection meaningfully for some MODERATE-severity faults that were reasonably
well-detected at the looser setting (condfouling50: 0.93->0.15; undercharge20:
0.90->0.21 when moving from contamination=0.05 to 0.01). This is a genuine product
decision (acceptable false-alarm rate vs. early detection of moderate faults), not
resolved here - belongs with whoever owns the eventual alert engine's UX.

**Consistent with the rest of this modeling phase**: every model built (6 binary
classifiers, this anomaly detector) struggles with the same mild/weak-signal cases
the EDA already identified as difficult - a reassuring sign that the EDA's findings
are correctly driving model behavior, not an unexplained failure specific to this
model.

## Experimental Dataset Models

Separate section - this dataset requires a genuinely different pipeline
(`ml/src/features/build_experimental_features.py`, not `build_features.py`) and
evaluation design (cross-season generalization, not TimeSeriesSplit), per
notebooks 07-10's EDA findings. No RTU_STG_STA/stage-2 filtering exists in this
dataset; season is the dominant confound, not raw weather.

### OA damper stuck (notebook 19)

- **Features**: `RTU_OA_DMPR_DM`, `RTU_OA_TEMP` (RTU_SA_TEMP deliberately excluded -
  proven fully compensated/masked per notebook 08's EDA).
- **Evaluation design**: cross-season generalization - trained on Winter_2022 +
  Spring_2021, evaluated on held-out Summer_2021 (never examined for this fault in
  the EDA). Fall_2020 excluded entirely (flagged as structurally atypical in
  notebook 07).
- **Raw features**: baseline precision 1.00, recall 0.11 - the model almost never
  recognizes Summer's genuine baseline as normal. Directly explained by notebook
  07's finding: Summer's baseline damper position sits near its ~6-7% minimum
  (OA_TEMP rarely below the 50°F enable threshold), while the model learned "normal
  = ~22% active" from Winter/Spring - so Summer's real normal looks like a mild
  damper-stuck fault.
- **OA_TEMP-residualized features** (regression of damper position on OA_TEMP,
  fit on training-season baseline only): partial improvement - baseline recall
  0.11 -> 0.34, but baseline precision drops 1.00 -> 0.42. A real, INCOMPLETE fix -
  genuine precision/recall tradeoff, not a clean solution.
- **Status**: NOT production-usable as a single cross-season model without further
  work. Real, honest limitation - either accept one of the two tradeoffs above, or
  build season-specific baselines/thresholds (not yet attempted). Flagged as an
  open item, same standard as undercharge's unresolved Simulated-dataset case.

### Biased SAT sensor (notebook 20)

- **Features**: `RTU_TOT_WATT`, `RTU_SA_TEMP` - RTU_TOT_WATT was the most robust
  cross-season finding in notebook 10's EDA.
- **Evaluation design**: same cross-season generalization as notebook 19 - trained
  on Winter_2022 + Spring_2021, evaluated on held-out Summer_2021.
- **Raw features**: baseline recall ~0.00, precision 0.12 - near-total collapse,
  same pattern as OA damper stuck. Plausible cause: RTU_TOT_WATT is naturally much
  higher in Summer baseline (real cooling load) than in Winter/Spring baseline, so
  the model learned "normal = low/moderate power" from cooler seasons and mistakes
  Summer's genuinely normal higher power draw for the fault's effect.
- **OA_TEMP-residualized features**: only a small improvement (recall 0.00->0.05,
  precision 0.12->0.34) - MUCH weaker than OA damper stuck's residualization
  (0.11->0.34). Likely because RTU_TOT_WATT's relationship with weather is more
  complex (cooling load depends on humidity, occupancy, and nonlinear effects) than
  a simple linear regression against OA_TEMP captures.
- **Status**: NOT production-usable as a single cross-season model. Genuinely
  harder, less-mitigated problem than OA damper stuck - flagged as an open item
  requiring either a more sophisticated weather/load model or season-specific
  thresholds, not resolved here.

### Incorrect economizer setpoint (notebook 21)

This fault required splitting into two separate sub-models, since notebook 09's EDA
found the "too low" and "too high" severities behave in opposite, unexplained ways
AND require different seasons to have a valid test window at all.

**Setpoint too low (6°C, 8°C)**: cross-season model, trained on Winter_2022,
evaluated on held-out Spring_2021 (both confirmed valid per the EDA). Features:
`RTU_OA_DMPR_DM`, `RTU_OA_TEMP`. Result: baseline recall 0.40, precision 0.87 - a
moderate, real result, better than OA damper stuck's raw-feature collapse but worse
than a clean success. Plausibly explained by this fault direction's own
already-unusual EDA behavior (unexplained over-engagement extending past both the
fault's own and the correct setpoint).

**Setpoint too high (12°C, 14°C)**: NOT modeled. Per notebook 09, only Fall_2020
was confirmed to provide a valid test window for these severities (Winter_2022
never got cold enough post-occupied-hours-filtering). No genuine cross-season
evaluation is possible with only one valid season - building one anyway would
either misuse an invalid season or amount to a within-season random split, which
would overstate real-world readiness the same way random splits did throughout the
Simulated-dataset work. Documented as a real, honest data-availability limitation,
not a modeling failure - would need a second valid season of data collection before
this direction can be evaluated honestly.

- **Status**: partially modeled. One direction usable-but-imperfect; the other
  genuinely unmodelable with currently available data.

## Modeling phase status: all 3 Experimental-dataset faults addressed

OA damper stuck (partially mitigated), biased SAT sensor (largely unresolved),
incorrect economizer setpoint (one direction modeled with a moderate result, the
other direction correctly identified as unmodelable given current data
availability). This completes the modeling pass across both the Simulated dataset
(6 binary classifiers + Isolation Forest) and the Experimental dataset, to the
extent the available data supports honest evaluation.

## Not yet done

Consolidated final evaluation-metrics summary (precision/recall/F1/false-alarm rate
across all models in one place) - SHAP/feature-importance output - alert engine -
Field-dataset validation (reserved exclusively for validation once a model exists,
per the original project scope - not yet begun).

## Capacity feature bug fix (post-publication correction)

**Found while building the live-inference feature pipeline** (notebooks 24-25),
via a cross-validation test comparing the live pipeline's output against
build_feature_table()'s batch output for the same real row - the two disagreed
on the capacity feature specifically.

**Root cause**: build_feature_table() called stage2_only() BEFORE
add_segmented_ewma(), the opposite order from notebook 01's original,
validated approach (smooth on the full unfiltered series first, filter
after). Filtering first left every remaining row in the same state bucket
(stage-2), eliminating the real state transitions segmented EWMA needs to
correctly separate distinct operating sessions - silently blending together
what were actually separate real stage-2 sessions (each surrounded by
now-removed off/stage-1 periods) into one continuous smoothing run.

**Fixed**: build_feature_table() now smooths on the full series first, then
filters. Verified via a full kernel-restart re-run that the live and batch
pipelines now produce identical results for the same real row.

**Affected models, retrained and re-evaluated** (any model including capacity
as a feature):
- **Condenser fouling**: conclusion unchanged (stable, no collapse). Recall
  actually improved slightly (1.00 across all folds, up from 0.99-1.00).
  Precision drift widened (0.95->0.76, vs originally 0.96->0.88) - a real,
  honest change reflecting more faithful representation of natural session-
  to-session variation.
- **Liquid-line restriction**: conclusion unchanged. Recall essentially
  unchanged. Precision drift modestly widened (0.98->0.91, vs originally
  0.98->0.96).
- **Isolation Forest**: genuine improvement - false-positive rate roughly
  halved (6.1%->2.9%), no loss of strong-fault detection.

**No model flipped status** as a result of this fix - all three remain
"Usable"/"Usable with caveat" per FINAL_MODEL_METRICS.md, now updated with
the corrected numbers.

**Why this matters beyond the immediate fix**: this bug had been silently
present since notebook 11 first extracted build_feature_table(), through 13+
notebooks of EDA and modeling work, undetected by any of the extensive
TimeSeriesSplit/ablation testing already done - because all of that testing
compared the function's output against itself consistently, never against an
independent ground truth. The live-vs-batch cross-validation check is what
caught it, a direct justification for building that verification rather than
trusting the pipeline's internal consistency alone.

## Isolation Forest contamination re-tuning (second correction, same day)

**Notebook 25's re-verification of the Isolation Forest after the capacity-
feature bug fix was insufficient** - it only spot-checked 2 of 24 fault-
severity files (suctionpipe09bar, already at 100% both before and after;
overcharge10, already near the noise floor both before and after). Neither
spot-check could reveal a regression concentrated in the moderate tier.

**Found via notebook 26** (while validating the inference pipeline):
contamination=0.01 (carried over unchanged from before the capacity fix) was
severely miscalibrated against the corrected feature. Full 24-file sweep
revealed a severe regression across nearly the entire moderate tier:

| Fault | Pre-fix (buggy capacity) | Post-fix, contamination=0.01 (broken) |
|---|---|---|
| evapfouling40 | 0.99998 | 0.404 |
| evapfouling30 | 0.9985 | 0.211 |
| evapfouling20 | 0.738 | 0.020 |
| liquidpipe08bar | 0.422 | 0.207 |
| condfouling50 | 0.154 | 0.011 |

**Root cause**: the corrected capacity feature has wider, more faithful
natural baseline variance (consistent with the classifiers' own wider
precision drift after the same fix). contamination=0.01's threshold, tuned
against the OLD narrower distribution, no longer matched the new one.

**Tested two fixes directly, same rigor as the classifier capacity-ablation
test**: (1) re-tune contamination against the corrected feature, (2) drop
capacity from the Isolation Forest's features entirely (mirroring the
classifier fix for evaporator/suction-line restriction). Option 2 was
clearly worse - evapfouling40 detection collapsed to 0% (capacity is
essential for detecting evaporator-related faults via this method,
consistent with evaporator fouling's EDA-established strongest signal being
capacity). Option 1, contamination=0.03, restored near-original detection
across the full 24-file sweep at a real, disclosed FPR cost.

**Adopted and verified**: contamination=0.03. Retrained via
train_final_models.py and re-verified against the ACTUAL SAVED model
artifact (not just an in-notebook instance) across the complete 24-file
sweep - not a partial spot check this time. FPR ~6-7.6% (two test runs gave
slightly different values, a minor unexplained wobble not chased further).
Detection profile closely matches the original, pre-bug shape.

**Real, repeated lesson**: a 2-file "one strong, one weak" spot check is not
sufficient verification when a regression could be concentrated in the
untested middle tier. The full sweep should be the standard going forward
for any change touching a shared feature used across many fault types.

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

## Not yet modeled

Experimental-dataset faults (OA damper stuck, incorrect economizer setpoint, biased
SAT sensor), which will need season-awareness built into the pipeline per that
dataset's EDA findings, not yet incorporated into `build_feature_table()`.

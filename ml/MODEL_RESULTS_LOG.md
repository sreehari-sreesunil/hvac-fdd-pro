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
metrics alone. This was established after notebook 11 (undercharge) found the two can
diverge dramatically.

## Undercharge (notebook 11)

- **Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, `RTU_REFG_DISC_PRES`,
  capacity (segmented-EWMA-smoothed, weather-residualized).
- **Random split**: reasonable (~34-81% baseline recall/precision, per various model
  attempts).
- **TimeSeriesSplit**: collapses from fold 1 (baseline recall 0.44) to fold 5
  (0.00) - a real, significant forward-in-time generalization failure.
- **Root cause**: partially isolated. Weather-driven variance in baseline behavior
  (`RTU_OA_TEMP` explains 77-99% of several features' baseline variance) is
  comparable in magnitude to undercharge's fault effect size. Residualizing against
  weather measurably improves near-term folds but does not fully resolve
  farther-future degradation. **Genuinely unresolved** - flagged as a real,
  documented risk, not fixed.
- **Status**: NOT production-usable as-is. Real methodological finding, valuable in
  its own right, but no trustworthy classifier produced.

## Overcharge (notebook 12)

- **Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, `RTU_REFG_DISC_PRES`
  (weather-residualized). Capacity excluded - not established as overcharge's
  strongest signal per notebook 02's EDA (capacity's non-monotonicity was mostly a
  staging confound, not a strong standalone signal).
- **Random split**: baseline recall 0.73, precision 0.89 (F1=0.80).
- **TimeSeriesSplit**: baseline recall 0.97-1.00 across all 5 folds - outperforms the
  random split, the OPPOSITE pattern from undercharge. No degradation trend.
- **Key finding**: undercharge's forward-in-time collapse is NOT a universal property
  of this dataset/pipeline - it appears specific to undercharge's relationship with
  weather-driven variance. Must be checked per fault, not assumed either way.
- **Minor open item**: baseline precision dips in folds 1 and 5 (0.65, 0.68) vs. folds
  2-4 (0.78-0.88) - more false alarms in those periods, not yet explained, not
  blocking.
- **Status**: genuinely usable working model, with a documented minor caveat.

## Condenser fouling (notebook 13)

- **Features**: `RTU_REFG_COND_PRES`, `RTU_REFG_COND_TEMP` (weather-residualized) -
  the strong, cleanly monotonic signals per notebook 03's EDA. Capacity included
  despite being flagged as weak between adjacent mid-severities (30% vs 40%,
  d=-0.037 in the EDA) - kept in to see if the model extracts any residual value.
- **Random split**: baseline recall 0.98, precision 0.99 (near-perfect).
- **TimeSeriesSplit**: baseline recall 0.99-1.00 across all 5 folds - no
  degradation trend, consistent with overcharge's pattern, not undercharge's.
- **Mild, non-blocking open item**: baseline precision drifts down slightly across
  folds (0.96 to 0.88) - a few more false alarms in later periods, much gentler than
  overcharge's fold 1/5 dip, not chased further.
- **Status**: strongest, most stable working model of the first three faults.

## Evaporator fouling (notebook 14)

- **Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, `RTU_SA_TEMP`, capacity
  (all weather-residualized) - per notebook 04's EDA, this fault has the STRONGEST
  capacity signal in the whole Simulated dataset (30% vs 40% Cohen's d = 1.376,
  "large" - the opposite of condenser fouling's near-zero at the same comparison).
- **Random split**: baseline recall 0.71, precision 0.90 (F1=0.79).
- **TimeSeriesSplit**: baseline recall degrades gradually across folds (0.76, 0.60,
  0.53, 0.45, 0.41) - a real trend, but plateaus rather than collapsing to zero like
  undercharge. Precision stays consistently high throughout (0.93-0.97) - the model
  becomes less sensitive to baseline over time, not confidently wrong.
- **Key finding, complicating the emerging hypothesis**: this fault has the
  dataset's strongest capacity signal, yet still shows real forward-in-time
  degradation - contradicting the simple "strong signal -> stable generalization"
  pattern suggested by overcharge/condenser fouling. Signal strength alone does not
  fully predict generalization behavior. Root cause not yet identified - flagged as
  a genuinely open question, to revisit once all 6 faults are modeled and there is a
  full picture to compare against.
- **Status**: usable model with an honestly-reported caveat - positioned between
  condenser fouling's stability and undercharge's collapse, not cleanly matching
  either.

## Cross-fault pattern so far (4 of 6 faults modeled)

| Fault | Random split baseline recall | TS fold range (baseline recall) | Trend |
|---|---|---|---|
| Undercharge | ~0.34-0.55 (varies by model) | 0.44 -> 0.00 | Collapses |
| Overcharge | 0.73 | 0.97 - 1.00 | Stable (improves vs random) |
| Condenser fouling | 0.98 | 0.99 - 1.00 | Stable, mild precision drift |
| Evaporator fouling | 0.71 | 0.76 -> 0.41 | Gradual decline, plateaus |

Three distinct generalization behaviors observed, not a simple binary - what
determines which pattern a given fault falls into is not yet understood. Worth a
dedicated investigation once liquid-line and suction-line restriction are modeled.

## Not yet modeled

Liquid-line restriction, suction-line restriction - Isolation Forest anomaly
detector - Experimental-dataset faults (OA damper stuck, incorrect economizer
setpoint, biased SAT sensor), which will need season-awareness built into the
pipeline per that dataset's EDA findings, not yet incorporated into
`build_feature_table()`.

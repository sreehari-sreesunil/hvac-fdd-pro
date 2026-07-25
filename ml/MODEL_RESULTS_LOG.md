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
  strongest signal per notebook 02's EDA.
- **Random split**: baseline recall 0.73, precision 0.89 (F1=0.80).
- **TimeSeriesSplit**: baseline recall 0.97-1.00 across all 5 folds - outperforms the
  random split. No degradation trend.
- **Minor open item**: baseline precision dips in folds 1 and 5 (0.65, 0.68) vs. folds
  2-4 (0.78-0.88) - not yet explained, not blocking.
- **Status**: genuinely usable working model, with a documented minor caveat.

## Condenser fouling (notebook 13)

- **Features**: `RTU_REFG_COND_PRES`, `RTU_REFG_COND_TEMP` (weather-residualized) -
  the strong, cleanly monotonic signals per notebook 03's EDA. Capacity included
  despite being flagged as weak between adjacent mid-severities.
- **Random split**: baseline recall 0.98, precision 0.99 (near-perfect).
- **TimeSeriesSplit**: baseline recall 0.99-1.00 across all 5 folds - no
  degradation trend.
- **Mild, non-blocking open item**: baseline precision drifts down slightly across
  folds (0.96 to 0.88).
- **Status**: strongest, most stable working model of the first three faults.

## Evaporator fouling (notebook 14)

- **Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, `RTU_SA_TEMP`, capacity
  (all weather-residualized) - this fault has the STRONGEST capacity signal in the
  whole Simulated dataset (Cohen's d=1.376 at the toughest adjacent-severity gap).
- **Random split**: baseline recall 0.71, precision 0.90 (F1=0.79).
- **TimeSeriesSplit**: baseline recall degrades gradually across folds (0.76, 0.60,
  0.53, 0.45, 0.41) - a real trend, but plateaus rather than collapsing to zero.
  Precision stays consistently high throughout (0.93-0.97).
- **Key finding**: strongest capacity signal in the dataset, yet still shows real
  forward-in-time degradation - contradicts a simple "strong signal -> stable"
  hypothesis.
- **Status**: usable model with an honestly-reported caveat.

## Liquid-line restriction (notebook 15)

- **Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, `RTU_REFG_DISC_PRES`,
  capacity (weather-residualized) - per notebook 05's EDA, this fault has a genuine
  THRESHOLD effect (minimal change at 1-4 bar, sharp jump at 8-10 bar), unlike the
  four continuously-scaling faults modeled before it.
- **Random split**: baseline recall 0.98, precision 0.99 (near-perfect).
- **TimeSeriesSplit**: baseline recall 0.99-1.00 across all 5 folds - no
  degradation trend, matching condenser fouling's stable pattern.
- **Key finding**: despite the threshold-shaped severity response (half the fault
  data barely differs from baseline), the model generalizes cleanly forward-in-time.
  This suggests severity shape (threshold vs. continuous) is NOT what determines the
  stable-vs-degrading split observed so far.
- **Status**: stable, near-perfect result - matches condenser fouling, not
  undercharge or evaporator fouling.

## Cross-fault pattern so far (5 of 6 faults modeled)

| Fault | Random split baseline recall | TS fold range (baseline recall) | Trend |
|---|---|---|---|
| Undercharge | ~0.34-0.55 (varies by model) | 0.44 -> 0.00 | Collapses |
| Overcharge | 0.73 | 0.97 - 1.00 | Stable |
| Condenser fouling | 0.98 | 0.99 - 1.00 | Stable |
| Evaporator fouling | 0.71 | 0.76 -> 0.41 | Gradual decline |
| Liquid-line restriction | 0.98 | 0.99 - 1.00 | Stable |

**Current split: 3 stable, 1 gradual decline, 1 collapse.** Neither signal strength
(evaporator fouling has the strongest signal yet degrades) nor severity shape
(liquid-line restriction is threshold-shaped yet stable) explains the pattern.
Genuinely open question - one fault remaining (suction-line restriction) before a
real pattern might emerge, or this may need a dedicated investigation once all 6
are modeled.

## Not yet modeled

Suction-line restriction - Isolation Forest anomaly detector - Experimental-dataset
faults (OA damper stuck, incorrect economizer setpoint, biased SAT sensor), which
will need season-awareness built into the pipeline per that dataset's EDA findings,
not yet incorporated into `build_feature_table()`.

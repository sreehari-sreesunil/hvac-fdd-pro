# Model Results Log (Simulated Dataset, One-vs-Rest Binary Classifiers)

Running log, updated after each fault is modeled. Architecture decision: one binary
classifier per fault (not a single multi-class model), since each fault needs
different, EDA-informed features per the cross-fault EDA summary. All models use
`build_feature_table()` (`ml/src/features/build_features.py`) — stage-2 filtering,
segmented EWMA smoothing, and weather-residualization applied uniformly, with
per-fault feature column choices informed by that fault's own EDA notebook.

**Standing evaluation practice**: report both a random train/test split (a diagnostic
upper bound, not representative of real deployment) and 5-fold `TimeSeriesSplit`
(the honest, forward-in-time evaluation) for every fault — never rely on random-split
metrics alone. This was established after notebook 11 (undercharge) found the two can
diverge dramatically.

## Undercharge (notebook 11)

- **Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, `RTU_REFG_DISC_PRES`,
  capacity (segmented-EWMA-smoothed, weather-residualized).
- **Random split**: reasonable (~34-81% baseline recall/precision, per various model
  attempts).
- **TimeSeriesSplit**: collapses from fold 1 (baseline recall 0.44) to fold 5
  (0.00) — a real, significant forward-in-time generalization failure.
- **Root cause**: partially isolated. Weather-driven variance in baseline behavior
  (`RTU_OA_TEMP` explains 77-99% of several features' baseline variance) is
  comparable in magnitude to undercharge's fault effect size. Residualizing against
  weather measurably improves near-term folds but does not fully resolve
  farther-future degradation. **Genuinely unresolved** — flagged as a real,
  documented risk, not fixed.
- **Status**: NOT production-usable as-is. Real methodological finding, valuable in
  its own right, but no trustworthy classifier produced.

## Overcharge (notebook 12)

- **Features**: `RTU_REFG_SUCT_PRES`, `RTU_REFG_SUCT_TEMP`, `RTU_REFG_DISC_PRES`
  (weather-residualized). Capacity excluded — not established as overcharge's
  strongest signal per notebook 02's EDA (capacity's non-monotonicity was mostly a
  staging confound, not a strong standalone signal).
- **Random split**: baseline recall 0.73, precision 0.89 (F1=0.80).
- **TimeSeriesSplit**: baseline recall 0.97-1.00 across all 5 folds — outperforms the
  random split, the OPPOSITE pattern from undercharge. No degradation trend.
- **Key finding**: undercharge's forward-in-time collapse is NOT a universal property
  of this dataset/pipeline — it appears specific to undercharge's relationship with
  weather-driven variance. Must be checked per fault, not assumed either way.
- **Minor open item**: baseline precision dips in folds 1 and 5 (0.65, 0.68) vs. folds
  2-4 (0.78-0.88) — more false alarms in those periods, not yet explained, not
  blocking.
- **Status**: genuinely usable working model, with a documented minor caveat.

## Not yet modeled

Condenser fouling, evaporator fouling, liquid-line restriction, suction-line
restriction — Isolation Forest anomaly detector — Experimental-dataset faults (OA
damper stuck, incorrect economizer setpoint, biased SAT sensor), which will need
season-awareness built into the pipeline per that dataset's EDA findings, not yet
incorporated into `build_feature_table()`.

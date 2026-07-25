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

## Cross-fault pattern: all 6 Simulated faults modeled

| Fault | Random split baseline recall | TS fold range (baseline recall) | Pattern |
|---|---|---|---|
| Undercharge | ~0.34-0.55 | 0.44 -> 0.00 | Collapses |
| Overcharge | 0.73 | 0.97 - 1.00 | Stable |
| Condenser fouling | 0.98 | 0.99 - 1.00 | Stable |
| Evaporator fouling | 0.71 | 0.76 -> 0.41 | Gradual decline |
| Liquid-line restriction | 0.98 | 0.99 - 1.00 | Stable |
| Suction-line restriction | 0.82 | 0.87 -> 0.43 | Gradual decline |

**Final split: 3 stable, 2 gradual decline, 1 full collapse.**

**Ruled out as explanations**: signal strength alone (evaporator fouling and
suction-line restriction have the two strongest signals in the dataset, yet both
degrade); severity shape (liquid-line restriction is threshold-shaped yet stable).

**Real, falsifiable hypothesis, not yet proven causal**: the three degrading/
collapsing faults (undercharge, evaporator fouling, suction-line restriction) ALL
directly produce large-magnitude capacity swings on the evaporator/suction side of
the refrigerant loop as their primary or a major effect. The three stable faults
(overcharge, condenser fouling, liquid-line restriction) do NOT have capacity as a
large-magnitude primary effect - overcharge's capacity effect was weak/non-
monotonic, condenser fouling's was consistently mild, liquid-line restriction's was
substantially reduced after stage-2 filtering. Plausible mechanism: capacity's own
substantial weather-driven variance (R²=0.767-0.988 against RTU_OA_TEMP across
different features, per notebook 11) may interact poorly with a LARGE fault effect
specifically, in a way residualization only partially corrects - even though
residualization worked cleanly for faults where capacity's fault-effect was small
or absent.

**Not yet tested, a real next step**: deliberately excluding capacity as a feature
for undercharge, evaporator fouling, and suction-line restriction, and checking
whether their TimeSeriesSplit degradation disappears - a direct, falsifiable test
of this hypothesis rather than a correlational observation across 6 data points.

## Not yet modeled

Isolation Forest anomaly detector - Experimental-dataset faults (OA damper stuck,
incorrect economizer setpoint, biased SAT sensor), which will need season-awareness
built into the pipeline per that dataset's EDA findings, not yet incorporated into
`build_feature_table()`.

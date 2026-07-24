# Cross-Fault Summary: LBNL Simulated RTU Dataset EDA

All six planned fault types from the Simulated dataset have now been examined
(notebooks 01-06). This document synthesizes findings across all six rather than
repeating each notebook's detail — see the individual notebooks for full methodology,
plots, and honestly-unresolved open questions.

## Fault mechanisms represented

Three genuinely different physical mechanisms, not six variations on one theme:

1. **Charge-level** (too little/too much refrigerant): undercharge, overcharge
2. **Heat-transfer surface degradation** (fouling): condenser fouling, evaporator fouling
3. **Physical restriction** (blockage in a line): liquid-line restriction, suction-line restriction

## Comparison table: strongest capacity effect (`RTU_TOT_CAPA`), stage-2 filtered

| Fault | Max severity | Capacity effect at max severity | Shape |
|---|---|---|---|
| Undercharge | 20% | -6.6% (raw, not reconciled to pooled-std here) | Monotonic |
| Overcharge | 20% | not the strongest signal for this fault (see below) | Non-monotonic even filtered |
| Condenser fouling | 50% | -4.46% | Monotonic unfiltered; **non-monotonic filtered** (real, checked wobble at 30-40%) |
| Evaporator fouling | 50% | -18.59% | Monotonic, strong, clean at every severity |
| Liquid-line restriction | 10 bar | -7.49% | **Threshold effect** — minimal change at 1-4 bar, sharp shift at 8-10 bar |
| Suction-line restriction | 9 bar | **-50.62%** | Monotonic, strongest and cleanest signal found in the dataset |

**Suction-line restriction produces by far the largest capacity effect found** — nearly
3x evaporator fouling's, and ~7x liquid-line restriction's peak. Undercharge/overcharge
never made capacity their strongest signal at all; other columns carried those faults'
real signatures instead.

## Which faults need stage-2 filtering, and which direction it moves the result

Filtering direction is **not predictable from fault type alone** — checked individually
every time, per this project's working discipline, rather than assumed:

| Fault | Filtering's effect on capacity |
|---|---|
| Undercharge | Filtering *reveals* signal obscured by cross-regime noise (raw d≈1.33 pooled → segmented-EWMA d≈1.41 pooled) |
| Overcharge | Filtering *shrinks* the anomaly (20%-severity capacity drop: ~4.4% loose filter → <0.5% strict filter) |
| Condenser fouling | Filtering *introduces* a real non-monotonic wobble (30% vs 40%, d=-0.037) not present unfiltered |
| Evaporator fouling | Filtering *sharpens* an already-clean signal, no confound found |
| Liquid-line restriction | Filtering *shrinks* the apparent effect (10-bar capacity: -18.38% unfiltered → -7.49% filtered) — more than half the raw effect was staging noise |
| Suction-line restriction | Filtering *grows* the effect (9-bar capacity: -31.80% unfiltered → -50.62% filtered) — staging blend was diluting the true signal |

## Which faults are "easy" vs. "hard" to classify, by adjacent-severity Cohen's d

| Fault | Weakest adjacent-severity gap found | d |
|---|---|---|
| Condenser fouling | 30% vs 40% (`RTU_TOT_CAPA`) | -0.037 (negligible) |
| Overcharge | Raw/EWMA suction temp effect sizes throughout | ~0.24-0.33 (small) |
| Undercharge | Raw capacity effect (baseline vs 20%, pooled) | 1.33 (large) |
| Liquid-line restriction | 1 bar vs 4 bar (mild severities, capacity barely moves) | not directly computed — flagged as a likely weak spot |
| Evaporator fouling | 30% vs 40% (`RTU_TOT_CAPA`) | 1.376 (large) |
| Suction-line restriction | 1 bar vs 3 bar (mildest gap tested) | 4.439 (extreme) |

Condenser fouling and overcharge are the two faults most likely to be confused with
adjacent severities or with each other on weak signals; suction-line restriction is
almost certainly the easiest fault to classify at any severity.

## Honestly unresolved questions carried forward (not resolved by EDA alone)

- **Overcharge**: why is `RTU_REFG_DISC_PRES` genuinely non-monotonic even under strict
  stage-2 filtering? (notebook 02)
- **Condenser fouling**: why does `RTU_TOT_CAPA` specifically fail to separate cleanly
  between 30% and 40% severity, when every other signal for this fault is clean?
  (notebook 03)
- **Liquid-line restriction**: why does the fault show a threshold effect (minimal
  change at 1-4 bar, sharp change at 8-10 bar) rather than a smooth trend? Plausible
  mechanism (flash gas onset) proposed but not confirmed. Also: `RTU_REFG_DISC_PRES`
  remains non-monotonic even filtered. (notebook 05)
- **EWMA span as a hyperparameter**: `span=30` helped undercharge, did not help
  overcharge at any span tested (30 or 10) — never resolved as a general default,
  flagged for a proper validation-based search once real feature engineering begins
  (notebooks 01, 02)

## Practical implications for the modeling phase

1. **`RTU_TOT_CAPA` needs stage-2 filtering treated as standard practice** before
   drawing any conclusion from it, for any fault — but the *direction* of correction
   must be checked per fault, never assumed.
2. **A single global severity-regression feature won't work uniformly** — liquid-line
   restriction's threshold behavior means a model tuned on high-severity examples could
   miss early-stage cases for that fault specifically.
3. **Some fault pairs may be genuinely hard to distinguish on weak signals** —
   condenser fouling and overcharge both have known weak spots; feature selection for
   the eventual classifier should lean on each fault's *strongest* signal (condenser
   pressure/temp for condenser fouling; suction pressure/temp for both restrictions;
   capacity for evaporator fouling and suction-line restriction) rather than one
   universal feature set.
4. **Effect-size convention matters and must stay consistent** — notebook 01/02
   originally used baseline-std Cohen's d; reconciled against the pooled-std
   convention (`ml/src/features/effect_size.py`) used from notebook 03 onward. Both
   are recorded honestly in-notebook rather than one silently overwriting the other.

## Next phase

All six Simulated-dataset fault types are now EDA'd. Per the original project scope,
next is the **Experimental dataset** (economizer/controls faults: OA damper stuck,
incorrect economizer setpoint, biased SAT sensor — 3 fault types, 4 severities each,
56 sensors, real Trane hardware) — a genuinely different data source (lab, not
simulation) and a different fault family (controls/sensor faults, not
mechanical/refrigerant faults). Zero work started on this as of this summary.

# Cross-Fault Summary: LBNL Experimental RTU Dataset EDA

All three planned fault types from the Experimental dataset have now been examined
(notebooks 08-10), following the baseline-across-seasons investigation in notebook 07.
This document synthesizes findings across all three — see individual notebooks for
full methodology, plots, and honestly-unresolved open questions.

## What makes this dataset fundamentally different from the Simulated dataset

- **Real lab hardware (ORNL's Flexible Research Platform), not simulation.** Real
  weather variation across recording days is a genuine confound that never existed in
  the Simulated dataset's single continuous 100-day run per fault.
- **One file per fault-severity-per-season**, not one continuous run per severity.
  Every comparison must be done within-season (confirmed necessary in notebook 07,
  after finding baseline itself varies substantially by season).
- **Real missing data by design** — a documented `"NAN"` sentinel string, which
  pandas' default `read_csv()` silently misreads as text rather than as missing,
  corrupting up to 53 of 57 columns per file if not explicitly handled
  (`na_values=["NAN"]`).
- **56 sensors, different naming conventions** than the Simulated dataset (e.g. no
  `ZA_TEMP`; instead 10 per-room `TERM_RM_TEMP_*` columns; `RTU_RA_TEMP` used as a
  single-signal proxy for space temperature instead).
- **Findings replicate across seasons far less reliably** than Simulated-dataset
  findings replicated across severities — every fault type in this dataset produced
  at least one real, checked exception when a second season was tested.

## Fault-by-fault summary

### OA damper stuck (notebook 08)
Four severities: forced damper positions (5%, 10%, 50%, 100% open).
- **Trivially detectable** via `RTU_OA_DMPR_DM` directly — confirmed exactly matching
  documented positions in two seasons (Winter_2022, Spring_2021).
- **`RTU_SA_TEMP` fully compensated/masked** in both seasons checked — a classifier
  relying on SAT alone would miss this fault entirely, regardless of severity.
- **`MA_TEMP - OA_TEMP`** (normalized for each file's real weather) showed a clean,
  monotonic relationship to damper position in both seasons — best secondary feature.
- One false lead (a rank-breaking anomaly at the 5% severity in Winter) did not
  replicate in Spring — resolved as a one-season artifact via the generalization
  check itself, more cheaply than direct investigation would have been.

### Incorrect economizer setpoint (notebook 09)
Four severities: setpoint values of 6°C, 8°C, 12°C, 14°C (correct: 10°C).
- **Most methodologically demanding fault examined in this dataset.** Required
  checking each file's actual OA_TEMP range (not just the mean) to confirm a valid
  test window even existed — Winter_2022 turned out to be an invalid test day for the
  "setpoint too high" severities (never got cold enough to distinguish correct from
  incorrect setpoint behavior); Fall_2020 provided a valid window instead.
- **"Setpoint too high" (12°C, 14°C)**: near-total suppression of economizer
  engagement, even in temperature windows where engagement should occur — confirmed
  not explained by the documented MA_TEMP>45°F gate condition.
- **"Setpoint too low" (6°C, 8°C)**: the opposite surprise — *more* engagement than
  baseline, extending well past both the fault's own and the correct setpoint, with
  one severity (8°C) showing an unexplained double-hump engagement pattern.
- **Neither direction matches a simple "shifted threshold" model.** Both are large,
  real, detectable effects on `RTU_OA_DMPR_DM` — but the underlying mechanism in
  both directions is genuinely unresolved, flagged for the feature-engineering phase
  rather than chased further in EDA.

### Biased SAT sensor (notebook 10)
Four severities: bias of +2°C, +4°C, -2°C, -4°C applied directly to the reported
SAT value (dataset contains the faulty reading, not ground truth).
- **`RTU_SA_TEMP` stays invisible to the fault in Winter_2022** (flat ~56°F across all
  severities, confirming the control loop chases the biased reading) — **but this did
  NOT fully replicate in Spring_2021**, where the most extreme severity (+4°C) showed
  a real 5.6°F deviation. A genuine, unexplained exception.
- **`RTU_TOT_WATT` is the most robust cross-season finding** — increases meaningfully
  and directionally with bias magnitude in both seasons checked (~1.4-2.2x baseline
  at the most severe settings), directly relevant to an "estimated energy impact"
  framing for a real copilot output.
- **`RTU_COMP_WATT_2`'s clean "forces an idle compressor on" story was Winter-specific**
  — did not generalize to Spring, where compressor 2 was already active at baseline.

## Cross-fault methodology lessons (generalizable beyond this dataset)

1. **Raw daily means are unsafe when the fault's effect depends on a real-world
   threshold crossing that may not occur on a given recording day.** A scatter against
   the actual triggering variable (e.g. OA_TEMP for economizer faults) is necessary,
   not optional, for any fault gated by an environmental condition.
2. **A file's full-day temperature range is not sufficient to confirm a valid test
   window** — occupied-hours-only range must be checked separately, since unoccupied
   hours can include conditions that never coincide with what's being tested.
3. **Generalization checks (a second season) are not optional confirmation — they are
   load-bearing.** Every fault type in this dataset produced at least one real
   exception when checked against a second season, several of which reversed or
   substantially qualified a Winter-only conclusion.
4. **A fault being invisible on its own "namesake" sensor is not a dead end — it's
   the actual finding.** OA damper stuck is invisible on SAT; biased SAT sensor is
   (mostly) invisible on SAT itself; both require a derived or adjacent signal for
   real detection. This is arguably the single most useful pattern from this dataset
   for the eventual FDD system's design.

## Practical implications for the modeling phase

1. **Season needs to be an explicit input or stratification variable**, not something
   pooled away — confirmed necessary in notebook 07 and reinforced by every fault
   type's generalization checks since.
2. **Feature selection per fault should favor the signal that actually carries
   information, not the signal the fault is named after** — `RTU_OA_DMPR_DM` (not
   SAT) for both OA damper stuck and economizer setpoint; `RTU_TOT_WATT` (not SAT)
   for biased SAT sensor.
3. **Confidence claims in the eventual copilot output should be fault- and
   season-aware**, not uniform — this dataset showed meaningfully less cross-season
   robustness than the Simulated dataset showed cross-severity robustness, which
   should inform how confidently the system communicates a diagnosis for these three
   fault types specifically versus the six Simulated-dataset faults.

## Next phase

Per the original project scope, the Field dataset (2 real buildings, 2 real fault
instances total) remains reserved exclusively for validation once a model exists —
not for further EDA or training data. With all 6 Simulated-dataset faults and all 3
Experimental-dataset faults now examined, the next real phase is feature engineering
and model training (per-fault feature selection informed by both cross-fault summary
documents, stage-2/season-aware preprocessing, and the two coordinated fault-family
models originally scoped: mechanical/refrigerant and economizer/controls).

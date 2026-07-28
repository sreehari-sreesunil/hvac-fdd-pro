# Model Acceptance Criteria

Written BEFORE the multi-algorithm comparison (Phase A2) begins, per an
external reviewer's recommendation. Purpose: define "good enough to ship"
in writing, in advance, so the upcoming model comparison can't unconsciously
move the goalposts to whatever the winning model happens to score.

These criteria are reverse-engineered from the real, already-correct
judgment calls in `FINAL_MODEL_METRICS.md` — they codify the standard you've
already been holding yourself to, not a new, stricter bar invented from
nothing. Existing status labels (Usable / Usable with caveat / Not
production-usable / Not modeled) are unchanged; this document makes the
numeric/qualitative reasoning behind each label explicit and repeatable.

## Mandatory evaluation methodology (non-negotiable, applies to every model)

- **Simulated dataset**: 5-fold `TimeSeriesSplit` is the only evaluation
  method that can assign a status label. A random-split result may be
  reported alongside it as a diagnostic upper bound ONLY — never used to
  justify "Usable" or any other label on its own.
- **Experimental dataset**: cross-season generalization (train on 1-2
  seasons, evaluate on a genuinely held-out season) is the equivalent
  requirement, since individual files are too short for a meaningful
  in-file time split.
- **Full-sweep verification standard**: any change touching a feature
  shared across multiple models (e.g. the capacity feature, weather
  residualization) MUST be re-verified against the full file set before a
  status label can be assigned or changed — a partial spot check (e.g. 2
  of 24 files) is explicitly insufficient. This is not a new rule; it's
  the standing lesson from the Isolation Forest contamination incident,
  now written down instead of just remembered.
- **Fold sample sizes must be reported alongside every metric.** A fold
  with very few positive examples can produce a misleadingly extreme
  number (e.g. 0.99998) that isn't representative — this must be flagged
  explicitly in the results log, not silently averaged into a headline
  figure.

## Status tiers — numeric criteria

### Usable
- Recall ≥ 0.90 in EVERY `TimeSeriesSplit` fold (or every held-out season,
  for Experimental models) — no fold may drop meaningfully below this,
  even if the average looks fine.
- Precision ≥ 0.75 in every fold. (Calibrated directly against Condenser
  Fouling's real 0.76 floor — already correctly labeled "Usable.")
- No fold shows collapse toward near-random performance.
- Minor, explained dips in 1-2 folds are acceptable (matches Overcharge's
  real "minor unexplained precision dip in 2 of 5 folds" — still Usable)
  PROVIDED the dip is investigated and explicitly written up, not just
  observed and ignored.

### Usable with caveat
- Recall ≥ 0.65 in every fold, precision ≥ 0.60 in every fold
  (calibrated against Suction-Line Restriction's real 0.63 floor).
- REQUIRES a written mitigation and the exact configuration needed to
  achieve these numbers (e.g. "must deploy WITHOUT the capacity feature")
  — a caveat that isn't specific and actionable doesn't qualify for this
  tier; it belongs in "Not production-usable" instead.
- The tradeoff being accepted (what's given up to get here) must be
  stated in the same entry — e.g. "precision cost: 0.93-0.97 -> 0.72-0.74."

### Not production-usable
- Any fold where recall OR precision collapses below the "Usable with
  caveat" floor above — this is the actual disqualifying pattern (a real
  collapse in at least one fold), not merely a lower average across folds.
  (Matches Undercharge's real 0.44 -> 0.00 collapse — the average recall
  wasn't the problem, the collapse was.)
- A tested mitigation that makes the problem WORSE, not better (as
  happened when capacity-removal was tried for Undercharge), is itself
  evidence supporting this label, not a reason to keep searching for a
  quick fix before the next milestone.
- Must include: root cause investigated to what depth, what remains
  unresolved, and what would need to be true to reconsider (matches the
  existing Undercharge entry's standard — keep meeting it, don't lower it).

### Not modeled
- Reserved for genuine data-availability gaps only (e.g. econ.-setpoint-
  too-high's single-season problem) — never used as a substitute label
  for a model that was tried and failed. If it was trained and evaluated,
  even badly, it gets one of the three labels above, not this one.

## Anomaly-detector-specific criteria (Isolation Forest / future candidates)

- False-positive rate on held-out baseline data: ≤ 10% for "Usable with
  caveat," ≤ 5% for "Usable" (current Isolation Forest at 6-7.6% sits in
  "Usable with caveat" territory under this bar — consistent with its
  current real label).
- Detection rate must be reported per severity tier (strong/moderate/weak
  signal faults), never as one blended average — a gatekeeper that only
  catches severe faults but is reported as "high detection rate" overall
  is misleading, exactly as your own existing entry already documents.

## Re-evaluation triggers (when a status label must be re-checked, not assumed to still hold)

- After any change to a shared feature-engineering function.
- After any hyperparameter change (directly relevant to the upcoming
  Phase A2 multi-algorithm comparison).
- After any retraining, for any reason.
- On a fixed cadence once real production telemetry exists (cadence TBD
  in Phase F's drift-detection design work).

## What this document does NOT do

- Does not retroactively change any current model's status — the existing
  labels in `FINAL_MODEL_METRICS.md` were checked against these criteria
  while writing this document and all remain consistent with it.
- Does not set a bar for algorithms not yet tried (Phase A2) — those will
  be judged against the same tiers above, fairly, whichever architecture
  wins per fault.

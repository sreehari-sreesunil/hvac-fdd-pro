# Anomaly Detector Comparison Log (Isolation Forest vs. One-Class SVM vs. LOF)

Triggered by the same external review feedback as MODEL_COMPARISON_LOG.md:
"develop a POC for anomaly detection and evaluate suitable models." The
gatekeeper had never been compared against alternatives.

## Methodology

- **Harness**: `ml/src/models/compare_anomaly_detectors.py`. Deliberately
  DIFFERENT evaluation shape from the classifier comparison, because
  anomaly detectors are unsupervised - trained ONLY on baseline
  (unfaulted) data, never shown a labeled fault during training.
- Trained on the first 80% of `RTU_sim_baseline.csv` (temporal split,
  never random). False-positive rate measured on the held-out final 20%
  - genuine held-out data the model never saw.
- Detection rate measured PER INDIVIDUAL FAULT FILE across all 21 files
  in the full severity sweep (undercharge excluded, matching the existing
  gatekeeper's own scope decision) - never blended into one average, per
  MODEL_ACCEPTANCE_CRITERIA.md's explicit requirement.
- Candidates: Isolation Forest (current shipped algorithm), One-Class SVM
  (RBF kernel), Local Outlier Factor (novelty=True).

## A real methodology bug found and fixed mid-comparison

The harness's first version auto-selected the "best" hyperparameter per
algorithm using ONLY held-out baseline FPR. This was wrong in a way worth
recording plainly: for a single-threshold anomaly detector, FPR and
detection rate move in the SAME direction as contamination/nu changes, so
"lowest FPR" has a trivial optimum - it will always pick the smallest grid
value, regardless of what's in the grid, providing no real selection
signal at all.

Worse, this silently reproduced a known, previously-fixed problem: all
three algorithms' auto-selected configs converged on the smallest
contamination/nu tested, and Isolation Forest's result at that setting
showed the same moderate-tier detection weakness the currently-shipped
model was already re-tuned away from once before (contamination=0.01's
documented "detection collapse" - see MODEL_RESULTS_LOG.md). The
selection method had walked straight back into a mistake this project
already paid to learn from.

Fixed by removing auto-selection entirely - every grid config is now
evaluated and reported, and the actual choice is a deliberate human
decision weighing FPR against detection rate together, the same way the
original Isolation Forest 0.01->0.03 retuning was actually decided.

## Full results (representative files - see MODEL_COMPARISON_ANOMALY_RESULTS.json for all 21)

### Isolation Forest
| contamination | FPR | Tier | evapfouling30 | liquidpipe10bar |
|---|---|---|---|---|
| 0.01 | 2.87% | Usable | 0.135 | 0.738 |
| 0.02 | 6.01% | Usable with caveat | 0.683 | 0.791 |
| 0.03 (currently shipped) | 7.76% | Usable with caveat | 1.000 | 0.827 |
| 0.05 | 10.11% | Not production-usable | 1.000 | 0.874 |

### One-Class SVM
| nu | FPR | Tier | evapfouling30 | liquidpipe10bar |
|---|---|---|---|---|
| 0.01 | 2.95% | Usable | 0.984 | 0.759 |
| 0.03 | 5.29% | Usable with caveat | 0.986 | 0.773 |
| 0.05 | 8.21% | Usable with caveat | 0.986 | 0.781 |

### Local Outlier Factor
| contamination, n_neighbors | FPR | Tier | evapfouling30 | liquidpipe10bar |
|---|---|---|---|---|
| 0.01, 20 | 1.49% | Usable | 0.982 | 0.755 |
| 0.03, 20 | 3.07% | Usable | 0.988 | 0.830 |
| 0.05, 20 | 6.86% | Usable with caveat | 0.996 | 0.915 |

## Decision

**SWITCHED to One-Class SVM (`nu=0.01`, `kernel=rbf`).** At an FPR
essentially matching Isolation Forest's own best achievable setting
(2.95% vs. 2.87%), SVM detects `evapfouling30` 98.4% of the time versus
Isolation Forest's 13.5% - a categorically different level of gatekeeper
performance, not a marginal improvement bought with a worse false-alarm
rate. This is the single most consequential change in this comparison
(more so than the classifier promotion) since this model is the sole
gatekeeper for the entire two-stage architecture (Section 2.4 of the
original project handoff), not one of several fault-specific classifiers.

**Local Outlier Factor was NOT chosen despite comparable or slightly
better detection numbers.** Its serialized model measured 11.9MB versus
SVM's 24.6KB - a ~483x difference - because `LocalOutlierFactor` with
`novelty=True` must embed its entire training set to compute neighbor
distances at prediction time. This is a structural cost, not a one-time
inconvenience: it gets worse with every future retrain as more baseline
data accumulates, unlike Isolation Forest or SVM. Same category of
reasoning that ruled out MLP for evaporator fouling in
MODEL_COMPARISON_LOG.md - comparable accuracy, real ongoing operational
cost, not worth it.

## Renaming

`ISOLATION_FOREST_CONFIG` -> `ANOMALY_GATEKEEPER_CONFIG`,
`simulated_isolation_forest` -> `simulated_anomaly_gatekeeper`, done now
while nothing downstream (no alert engine, no frontend integration) yet
depends on the old name - the cheapest this rename will ever be.

## A related bug found and fixed as a direct consequence of this promotion

`ml/src/models/inference.py` special-cased `isinstance(model,
IsolationForest)` to decide response shape (anomaly-score fields vs.
classifier fields). Switching the gatekeeper's underlying class to
`OneClassSVM` would have silently broken this - `OneClassSVM` has no
`predict_proba`, so it would have fallen into the classifier branch and
crashed on the first real request. Fixed by switching to a duck-typing
check (`hasattr(model, "predict_proba")`) that correctly generalizes to
any future anomaly-detector algorithm without needing this file edited
again.

---

## Addendum: Expanded feature set (triggered by A4 two-stage validation)

The original comparison above was run against a 3-feature gatekeeper
(SUCT_PRES, SUCT_TEMP, capacity). Building `validate_two_stage_architecture.py`
(see TWO_STAGE_ARCHITECTURE_VALIDATION_LOG.md) surfaced that this feature
set made the gatekeeper structurally blind to `condenser_fouling` (whose
real diagnostic signal is `COND_PRES`/`COND_TEMP`, columns never included)
and weak on `overcharge`/`liquidline_restriction` (partially reliant on
`DISC_PRES`, also excluded). Feature set expanded to the full union of
every classifier's own diagnostic columns: `SUCT_PRES`, `SUCT_TEMP`,
`DISC_PRES`, `COND_PRES`, `COND_TEMP`, `SA_TEMP`, plus capacity.

### Re-run results against the expanded 7-feature set

| Algorithm | Config | FPR | Tier |
|---|---|---|---|
| Isolation Forest | contamination=0.01 | 3.29% | Usable |
| Isolation Forest | contamination=0.02 | 5.51% | Usable with caveat |
| **Isolation Forest** | **contamination=0.03** | **7.78%** | **Usable with caveat** |
| Isolation Forest | contamination=0.05 | 11.31% | Not production-usable |
| One-Class SVM | nu=0.01 | 34.23% | Not production-usable |
| One-Class SVM | nu=0.03 | 44.49% | Not production-usable |
| One-Class SVM | nu=0.05 | 50.34% | Not production-usable |
| Local Outlier Factor | contamination=0.01-0.05 | 30.3-50.4% | Not production-usable |

**One-Class SVM and LOF's false-positive rates collapsed entirely** when
moving from 3 to 7 features (SVM: 2.95% -> 34.2% at the same `nu=0.01`).
This is a real, well-understood phenomenon, not a harness bug - distance
and kernel-based methods (SVM, LOF) suffer from the curse of
dimensionality, losing discriminative power as feature count grows, since
"how far is this from normal" becomes noisier in higher-dimensional
space. Isolation Forest, which partitions on individual axes rather than
relying on full-space distance, was far more robust - barely moved
(7.76% -> 7.78% at the same contamination).

### Decision: REVERTED to Isolation Forest, contamination=0.03

At the expanded feature set: `condfouling30` and `evapfouling30` both
reach 100% detection (up from ~2-6% and 13.5% respectively, pre-
expansion). `overcharge15` improves only marginally (2.1% -> 7.2%) -
flagged as a known, likely-structural limitation, not something this fix
solves. Status reverted from "Usable" (SVM) back to "Usable with caveat"
(Isolation Forest at 7.78% FPR crosses the 5% "Usable" ceiling but stays
within the 10% "Usable with caveat" ceiling) - an honest downgrade in
tier label in exchange for a gatekeeper that actually sees the columns
most of your faults live in, rather than one narrowly tuned to a feature
set that happened to match only `suctionline_restriction`.

System-level validation of this reverted config is in
TWO_STAGE_ARCHITECTURE_VALIDATION_LOG.md.

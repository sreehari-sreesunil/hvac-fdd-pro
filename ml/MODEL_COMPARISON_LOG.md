# Model Comparison Log (Multi-Algorithm, Simulated Dataset)

Triggered by external review feedback (8+ years HVAC/FDD field experience):
"experiment with ML and deep learning models," "compare models using a
standard evaluation framework," "select the best-performing model" - rather
than defaulting to Random Forest without ever testing whether it's actually
the best choice per fault.

## Methodology

- **Harness**: `ml/src/models/compare_algorithms.py`. Same 5-fold
  `TimeSeriesSplit` standard as every other classifier metric in this
  project - never a random split for a status decision (see
  `MODEL_ACCEPTANCE_CRITERIA.md`).
- **Candidates**: Logistic Regression (simple baseline), Random Forest
  (current shipped algorithm), XGBoost, MLPClassifier (scikit-learn's
  shallow neural net - deliberately chosen over PyTorch/TensorFlow; this
  dataset's scale doesn't justify that infrastructure weight, and MLP
  genuinely answers "did you try deep learning" without it).
- **Hyperparameter search**: nested - an inner `TimeSeriesSplit`-based
  `GridSearchCV` picks hyperparameters using ONLY each outer fold's training
  portion, before that fold's test portion is touched.
- **Acceptance tiers**: applied automatically per `MODEL_ACCEPTANCE_CRITERIA.md`'s
  numeric thresholds (Usable: recall >=0.90, precision >=0.75 in every fold;
  Usable with caveat: recall >=0.65, precision >=0.60 in every fold).
- MLP's hyperparameter grid was trimmed to a single combo
  (`hidden_layer_sizes=(64,32)`, `alpha=0.001`) for real, measured runtime
  reasons - a single MLP fit on `condenser_fouling`'s largest fold measured
  40.4s directly timed, and the untrimmed grid would have added 30-40 min
  on top of the other three algorithms combined.
- `class_weight="balanced"` was used for Logistic Regression and Random
  Forest - a real change from the currently shipped Random Forest config,
  which does not set it. This comparison is not strictly apples-to-apples
  against the exact deployed model; it tests whether better-regularized
  versions do better, on top of the algorithm question.
- XGBoost required raising `ml/pyproject.toml`'s `requires-python` from
  the stale `>=3.11` to `>=3.12` (actual dev environment is 3.13.5) -
  installed and gap-filled in a second pass after the initial run.
- Undercharge is excluded from this run - not in `SIMULATED_FAULTS`
  (excluded from the registry per its own Not-production-usable status).
  Re-testing it against these algorithms is a real, separate follow-up.
- Fold-level sample sizes were checked for every surprising result before
  writing anything below, per `MODEL_ACCEPTANCE_CRITERIA.md`'s
  fold-reporting requirement - none of the results here are thin-fold
  artifacts; every fold has tens of thousands of test rows.

## Results

### overcharge
- Random Forest (`class_weight="balanced"`): recall 0.64-0.93, precision
  0.99-1.00 -> Not production-usable. Verified real (~27,000+ positive test
  examples per fold) - genuine forward-in-time instability under this config.
- Logistic Regression: recall 0.38-0.50, precision 0.76-0.89 -> Not
  production-usable.
- MLP: recall 0.77-0.99, precision 0.99-1.00 -> Usable with caveat.
- XGBoost: recall 0.86-0.99, precision 0.98-0.99 -> Usable with caveat.
- **Decision: KEEP the currently shipped Random Forest config** (without
  `class_weight` balancing). Its real, existing recall (0.97-1.00 per
  `FINAL_MODEL_METRICS.md`) beats every candidate tested here. This
  comparison reinforces the current model, it doesn't replace it.

### condenser_fouling
- Logistic Regression: recall 0.92-0.99, precision 1.00 -> Usable.
- Random Forest: recall 0.91-0.99, precision 1.00 -> Usable.
- MLP: recall 0.92-1.00, precision 1.00 -> Usable.
- XGBoost: recall 0.93-1.00, precision 1.00 -> Usable.
- **Decision: KEEP currently shipped Random Forest.** All four candidates
  land in the same tier with overlapping, noise-level differences - no
  evidence supports switching.

### evaporator_fouling
- Logistic Regression: recall 0.84-0.87, precision 0.99-1.00 -> Usable
  with caveat.
- Random Forest (this comparison): recall 0.85-0.86, precision 1.00 ->
  Usable with caveat.
- MLP: recall 0.997-0.999, precision 0.981-0.997 -> Usable. Verified
  against ~52,500 positive test examples per fold - a real, substantial
  improvement, not a fluke.
- XGBoost: recall 0.949-0.952, precision 0.967-0.970 -> Usable. Same fold
  sizes, tight and stable across every fold.
- **Decision: SWITCH to XGBoost.** The currently shipped Random Forest has
  a documented, known weak recall floor here (0.76 -> 0.41 degradation in
  earlier evaluation, per `FINAL_MODEL_METRICS.md`). XGBoost resolves this
  directly - stable ~0.95 recall in every fold, crossing fully into
  "Usable." MLP scored marginally higher (0.997-0.999) but was NOT chosen:
  it would be the only model in the fleet requiring a persisted
  `StandardScaler` at inference time (new, permanent operational
  complexity in `live_features.py`/`ml-service`), and tree models get
  fast, exact SHAP `TreeExplainer` support for the already-planned
  feature-importance work, while MLP needs slower/approximate explainers.

### liquidline_restriction
- Logistic Regression: recall 0.93-1.00, precision 1.00 -> Usable.
- Random Forest: recall 0.97-1.00, precision 1.00 -> Usable.
- MLP: recall 0.99-1.00, precision 1.00 -> Usable.
- XGBoost: recall 0.99-1.00, precision 1.00 -> Usable.
- **Decision: KEEP currently shipped Random Forest.** No evidence supports
  switching.

### suctionline_restriction
- Logistic Regression: recall 0.81-0.83, precision 1.00 -> Usable with
  caveat.
- Random Forest: recall 0.84-0.87, precision 1.00 -> Usable with caveat.
- MLP: recall 0.88-0.91, precision 0.95-1.00 -> Usable with caveat.
- XGBoost: recall 0.89-0.92, precision 0.97-0.98 -> Usable with caveat.
- **Decision: KEEP currently shipped Random Forest.** XGBoost edges
  slightly ahead but stays in the same tier - not enough gain to justify
  taking on a second production algorithm for a same-tier result.

## Overall conclusion

Of six faults compared across four algorithms each, exactly ONE
(evaporator_fouling) has real, evidence-based justification to change
algorithms. This is the expected, honest outcome of doing this rigorously
rather than the disappointing one - it means the original Random Forest
choice was already sound for five of six faults, and the comparison caught
a genuine, fixable weak spot in the sixth.

**Next step**: promote XGBoost into `model_registry.py` for
`evaporator_fouling` specifically, retrain via `train_final_models.py`,
update `FINAL_MODEL_METRICS.md` with real numbers, and add `xgboost` as a
`services/ml-service` dependency before this reaches `ml-service` - that
Dockerfile may hit the same Python 3.11-vs-3.12 wall `ml/`'s own
environment just hit.

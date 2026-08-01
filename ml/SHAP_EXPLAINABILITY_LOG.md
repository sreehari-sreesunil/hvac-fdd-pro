# SHAP Feature-Importance Explainability

## Purpose

Turns a classifier's bare prediction ("condenser fouling: yes, 92%
probability") into something a technician can actually act on ("flagged
mainly because condenser temperature and pressure residuals were
unusually high"). Rooted in Shapley values (cooperative game theory -
how much did each "player"/feature contribute to the team's/model's
outcome). A direct answer to "how do you make this model's predictions
interpretable" - a common ML interview question, implemented here rather
than just discussed.

## Why TreeExplainer, not the general-purpose SHAP explainer

This project's classifiers are tree-based (RandomForest/XGBoost, per
ml/MODEL_COMPARISON_LOG.md). TreeExplainer computes EXACT Shapley values
for tree ensembles via a fast, specialized algorithm - not the
approximate sampling the general model-agnostic explainer uses for
arbitrary model types. Faster and more precise for what this project
actually trains.

## Scope: classifiers only, not the anomaly gatekeeper

The Isolation Forest gatekeeper is unsupervised - it doesn't have the
same clean Shapley-value support tree classifiers do (no predict_proba
to explain against in the same binary-classification sense). Explicitly
checked and returns a clear error message for this case rather than
silently producing a misleading result.

## Implementation

`ml/src/models/explainability.py`'s `explain()` reuses `load_model()`
and `build_live_features()` exactly as `inference.py`'s `predict()`
already does - the SAME feature vector, not a separate, potentially-
divergent pipeline. This wasn't incidental: inference.py's own
docstring already flagged "feature_values... a precursor to real SHAP/
feature-importance output, not a substitute for it" from when it was
first written, before this session's copilot work made building the
real thing worthwhile.

Wired into ml-service as `GET /predictions/{asset_id}/explain?model_name=...`.

## Verified live

`simulated_condenser_fouling` against the same test asset used
throughout this project. Real, domain-sensible result: top two
contributors were `RTU_REFG_COND_TEMP_residual` (0.077) and
`RTU_REFG_COND_PRES_residual` (0.072), far outweighing
`RTU_TOT_CAPA_ewma30_segmented_residual` (0.016) - condenser
temperature/pressure residuals dominating a CONDENSER FOULING
classifier's explanation is exactly what real physical/domain knowledge
would predict, not just "SHAP ran without erroring."

## Known follow-up, not done here

Not yet wired into copilot-service as a 5th tool (would let the chat
agent explain WHY a classifier fired, not just report baseline
deviation) - classifier predictions still need the "which model applies
to which asset" product decision flagged elsewhere in this project
before an agent tool calling them automatically makes sense. Adding a
SHAP-explanation tool once that's resolved is a natural, low-effort
follow-up - this module and endpoint already do the real work.

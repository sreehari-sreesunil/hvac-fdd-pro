"""SHAP-based feature-importance explanations for classifier predictions.

WHY SHAP specifically: it answers "why did the model predict this?" -
for one prediction, how much did each input feature push the outcome
toward or away from the predicted class. Rooted in Shapley values
(cooperative game theory - "how much did each player contribute to the
team's outcome"). Turns a bare probability into something a technician
can actually act on ("flagged mainly because condenser pressure was
unusually high"), not just a black-box number.

WHY TreeExplainer specifically, not the general model-agnostic SHAP
methods: this project's classifiers are tree-based (RandomForest/
XGBoost per ml/MODEL_COMPARISON_LOG.md) - TreeExplainer computes EXACT
Shapley values for tree ensembles via a fast, specialized algorithm,
rather than the approximate sampling the general-purpose explainer uses
for arbitrary model types. Faster and more precise for models this
project actually uses.

SCOPE: classifiers only, not the Isolation Forest anomaly gatekeeper -
unsupervised anomaly detection doesn't have the same clean SHAP support
tree classifiers do (no predict_proba to explain against in the same
way as a binary classifier). Flagged as a known limitation, not
silently ignored.

Reuses load_model() and build_live_features() from inference.py/
live_features.py exactly - the same feature vector inference.predict()
already computes, not a separate, potentially-divergent pipeline.
"""

from pathlib import Path

import pandas as pd
import shap
from sklearn.ensemble import IsolationForest

from src.features.live_features import build_live_features
from src.models.inference import load_model


def explain(model_name: str, buffer: pd.DataFrame, models_dir: Path) -> dict:
    """Explain one prediction: which features pushed the model's output
    toward or away from the predicted (fault) class, and by how much.

    Returns feature_contributions sorted by absolute magnitude
    (most-impactful-first) - a caller shouldn't need to know SHAP's own
    output-ordering conventions to find what mattered most.
    """
    model, metadata = load_model(model_name, models_dir)

    if isinstance(model, IsolationForest):
        return {
            "model": model_name,
            "error": (
                "SHAP explanations are not supported for the Isolation "
                "Forest anomaly gatekeeper - unsupervised models don't "
                "have the same clean Shapley-value support tree "
                "classifiers do. Only classifier models can be explained."
            ),
        }

    features = build_live_features(buffer, metadata)
    features_df = pd.DataFrame([features])[metadata["feature_cols"]]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features_df)

    # SHAP's output shape varies by version/model type - a list of
    # per-class arrays, or a single 3D array with class as the last
    # axis. Handle both defensively rather than assume one; class index
    # 1 is the "fault" class in every binary classifier this project
    # trains (see ml/MODEL_ACCEPTANCE_CRITERIA.md's label convention).
    if isinstance(shap_values, list):
        fault_class_values = shap_values[1][0]
    elif shap_values.ndim == 3:
        fault_class_values = shap_values[0, :, 1]
    else:
        fault_class_values = shap_values[0]

    contributions = [
        {
            "feature": feature_name,
            "value": float(features[feature_name]),
            "shap_contribution": float(contribution),
        }
        for feature_name, contribution in zip(metadata["feature_cols"], fault_class_values, strict=False)
    ]
    contributions.sort(key=lambda c: abs(c["shap_contribution"]), reverse=True)

    return {
        "model": model_name,
        "feature_contributions": contributions,
    }

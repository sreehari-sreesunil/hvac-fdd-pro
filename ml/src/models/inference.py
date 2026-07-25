"""Inference: load a saved model, apply the live feature pipeline, and
produce a structured prediction that carries its registry status/notes
alongside the raw result - a caller should never be able to treat a
"usable with caveat" model's output the same as a fully "usable" one
without at least seeing that distinction.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.features.live_features import build_live_features

# Arbitrary, unvalidated confidence thresholds - a placeholder product
# decision, not a calibrated result. Whoever owns the alert engine's UX
# should revisit these against real user feedback, the same way the
# Isolation Forest's contamination parameter was flagged as a real,
# unresolved tradeoff rather than a settled choice.
_CONFIDENCE_THRESHOLDS = {"high": 0.85, "moderate": 0.60}


def _confidence_label(probability: float) -> str:
    if probability >= _CONFIDENCE_THRESHOLDS["high"]:
        return "high"
    if probability >= _CONFIDENCE_THRESHOLDS["moderate"]:
        return "moderate"
    return "low"


def load_model(model_name: str, models_dir: Path) -> tuple[object, dict]:
    """Load a saved model and its metadata sidecar.

    Args:
        model_name: e.g. "simulated_condenser_fouling" - matches the
            <name>.joblib / <name>.metadata.json files saved by
            train_final_models.py.
        models_dir: Directory containing the saved model files.

    Returns:
        (model, metadata) tuple.
    """
    model = joblib.load(models_dir / f"{model_name}.joblib")
    with open(models_dir / f"{model_name}.metadata.json") as f:
        metadata = json.load(f)
    return model, metadata


def predict(model_name: str, buffer: pd.DataFrame, models_dir: Path) -> dict:
    """Score a live buffer of recent readings against one saved model.

    Args:
        model_name: Which saved model to use (see load_model()).
        buffer: Recent raw readings for one asset, sorted ascending by
            Datetime - see live_features.py for what each model needs.
        models_dir: Directory containing the saved model files.

    Returns:
        A dict always containing "model", "status", "notes" (the
        registry's own status/notes, so a caller can see any known
        caveat), and "feature_values" (the exact feature vector used - a
        precursor to real SHAP/feature-importance output, not a
        substitute for it). For classifiers, also "fault_probability",
        "predicted_label", and "confidence" (see _CONFIDENCE_THRESHOLDS -
        an unvalidated placeholder, not a calibrated result). For the
        Isolation Forest, also "is_anomaly" and "anomaly_score".
    """
    model, metadata = load_model(model_name, models_dir)
    features = build_live_features(buffer, metadata)
    features_df = pd.DataFrame([features])[metadata["feature_cols"]]

    result = {
        "model": model_name,
        "status": metadata["status"],
        "notes": metadata["notes"],
        "feature_values": features.to_dict(),
    }

    if isinstance(model, IsolationForest):
        raw_pred = model.predict(features_df)[0]
        anomaly_score = model.score_samples(features_df)[0]
        result["is_anomaly"] = bool(raw_pred == -1)
        result["anomaly_score"] = float(anomaly_score)
    else:
        fault_probability = float(model.predict_proba(features_df)[0][1])
        result["predicted_label"] = int(model.predict(features_df)[0])
        result["fault_probability"] = fault_probability
        result["confidence"] = _confidence_label(fault_probability)

    return result

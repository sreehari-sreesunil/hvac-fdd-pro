"""Inference: load a saved model, apply the live feature pipeline, and
produce a structured prediction that carries its registry status/notes
alongside the raw result - a caller should never be able to treat a
"usable with caveat" model's output the same as a fully "usable" one
without at least seeing that distinction.
"""

import json
import threading
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.features.live_features import build_live_features

# Arbitrary, unvalidated confidence thresholds - a placeholder product
# decision, not a calibrated result. Whoever owns the alert engine's UX
# should revisit these against real user feedback, the same way the
# Isolation Forest's contamination parameter was flagged as a real,
# unresolved tradeoff rather than a settled choice.
_CONFIDENCE_THRESHOLDS = {"high": 0.85, "moderate": 0.60}

# In-process cache, not Redis or any external store - this service runs
# as a single process/container with no horizontal scaling, so there's
# no second instance that would need a SHARED cache; a plain dict
# already solves this correctly at this scale (matches the project's
# established "no unnecessary heavy infra" philosophy - the alert
# scheduler chose in-process APScheduler over Celery/Redis for the same
# reason). Keyed on (model_name, resolved models_dir) rather than just
# model_name - critical for tests, which monkeypatch models_dir to a
# different temp directory per test; keying on model_name alone would
# silently return a stale model loaded from a PREVIOUS test's temp
# directory, a real correctness bug, not just a performance detail.
# No eviction/invalidation: models are static trained artifacts - if
# one is retrained and re-saved under the same filename, picking up the
# new version requires restarting the service, same as today (Python
# module state doesn't hot-reload) - an accepted, honest limitation,
# not silently different behavior from before this cache existed.
_model_cache: dict[tuple[str, str], tuple[Any, dict]] = {}
# Guards _model_cache's check-then-load-then-set pattern. Only matters
# now that load_model() is called from a thread pool (see ml-service's
# predictions.py) - genuinely concurrent requests can race on a cache
# miss for the same model, both redundantly deserializing it from disk.
# Not a correctness bug (each load produces a correct, independent
# model object), just wasted work - a plain in-process Lock is the
# right-sized fix, not anything heavier, matching this project's
# established "no unnecessary heavy infra" philosophy.
_model_cache_lock = threading.Lock()


def _confidence_label(probability: float) -> str:
    if probability >= _CONFIDENCE_THRESHOLDS["high"]:
        return "high"
    if probability >= _CONFIDENCE_THRESHOLDS["moderate"]:
        return "moderate"
    return "low"


def load_model(model_name: str, models_dir: Path) -> tuple[Any, dict]:
    """Load a saved model and its metadata sidecar, from cache if
    already loaded.

    Args:
        model_name: e.g. "simulated_condenser_fouling" - matches the
            <name>.joblib / <name>.metadata.json files saved by
            train_final_models.py.
        models_dir: Directory containing the saved model files.

    Returns:
        (model, metadata) tuple. model is typed Any, not object -
        it's genuinely one of several heterogeneous sklearn-compatible
        estimator types (RandomForest, XGBoost, Isolation Forest, etc.)
        with no shared base class, and predict()'s hasattr-based
        duck-typing on it is deliberate (see predict()'s own comment
        below). object would be statically "safer" but wrong here - it
        would claim mypy can verify nothing is called on the returned
        value, when predict() explicitly does call .predict()/
        .predict_proba()/.score_samples() on it based on runtime
        introspection, not a known static type. The SAME object
        references on a cache hit, not a copy - callers must not
        mutate the returned model or metadata dict, since that would
        corrupt it for every subsequent caller. Nothing in this
        codebase currently does, but worth stating explicitly now that
        a cache makes it a real hazard rather than a harmless one-off
        mutation.
    """
    cache_key = (model_name, str(models_dir))
    with _model_cache_lock:
        if cache_key in _model_cache:
            return _model_cache[cache_key]

        model = joblib.load(models_dir / f"{model_name}.joblib")
        with open(models_dir / f"{model_name}.metadata.json") as f:
            metadata = json.load(f)

        _model_cache[cache_key] = (model, metadata)
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

    if not hasattr(model, "predict_proba"):
        # Anomaly detectors (Isolation Forest, One-Class SVM, etc.) share no
        # common base class but all lack predict_proba - duck-typing here
        # means this branch stays correct automatically if the gatekeeper
        # algorithm changes again, without needing this file edited every
        # time (see ANOMALY_DETECTOR_COMPARISON_LOG.md for the most recent
        # such change, Isolation Forest -> One-Class SVM).
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

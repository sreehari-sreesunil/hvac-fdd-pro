"""Prediction endpoint: fetch real telemetry, assemble features, run
inference against a saved model."""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import security, verify_asset_access
from app.db.session import get_db
from app.models.prediction import Prediction
from app.services.buffer_builder import build_buffer

# ml/ is not an installable package - see docs/TECH_DEBT.md's
# "ml-service: sys.path import of ml/src instead of a proper package"
# entry for why this pattern was chosen deliberately, not by oversight.
if settings.ml_src_dir not in sys.path:
    sys.path.insert(0, settings.ml_src_dir)

from src.models.explainability import explain  # noqa: E402
from src.models.inference import load_model, predict  # noqa: E402

router = APIRouter()


@router.get("/predictions/{asset_id}")
async def get_prediction(
    asset_id: str,
    model_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> dict:
    """Score an asset's recent telemetry against one saved model, and
    persist the result.

    model_name must match a <name>.joblib/<name>.metadata.json pair in
    the models directory (e.g. "simulated_condenser_fouling") - explicit
    selection for now, not automatic "try every applicable model" -
    that's a real product decision for later, not assumed here.

    Persistence added here - previously every prediction was computed
    and returned but never saved, so no history existed to report on or
    to build the argmax-based fault-attribution fix on top of (see
    Prediction model's docstring). The response contract is unchanged;
    this is purely additive.
    """
    models_dir = Path(settings.models_dir)
    metadata_path = models_dir / f"{model_name}.metadata.json"
    if not metadata_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No saved model named '{model_name}'",
        )

    _, metadata = load_model(model_name, models_dir)
    required_raw_metrics = metadata.get("required_raw_metrics")
    if not required_raw_metrics:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model '{model_name}' metadata is missing required_raw_metrics",
        )

    buffer = await build_buffer(asset_id, required_raw_metrics, credentials.credentials)

    result = predict(model_name, buffer, models_dir)

    # result's shape varies by model type (classifier vs anomaly
    # detector) - see predict()'s docstring. .get() with a default of
    # None on every optional field means this works for either shape
    # without an if/else branch here duplicating that dispatch logic,
    # which already lives in inference.py and shouldn't be repeated.
    prediction_row = Prediction(
        asset_id=asset_id,
        model_name=model_name,
        predicted_label=result.get("predicted_label"),
        fault_probability=result.get("fault_probability"),
        confidence=result.get("confidence"),
        is_anomaly=result.get("is_anomaly"),
        anomaly_score=result.get("anomaly_score"),
        feature_values=result.get("feature_values"),
    )
    db.add(prediction_row)
    db.commit()

    return result


@router.get("/predictions/{asset_id}/explain")
async def get_prediction_explanation(
    asset_id: str,
    model_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _user_id: str = Depends(verify_asset_access),
) -> dict:
    """SHAP feature-importance for one prediction - which features
    pushed the model toward/away from the predicted class, and by how
    much. See ml/src/models/explainability.py for why SHAP/TreeExplainer
    specifically, and the classifier-only scope (not the Isolation
    Forest gatekeeper)."""
    models_dir = Path(settings.models_dir)
    metadata_path = models_dir / f"{model_name}.metadata.json"
    if not metadata_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No saved model named '{model_name}'",
        )

    _, metadata = load_model(model_name, models_dir)
    required_raw_metrics = metadata.get("required_raw_metrics")
    if not required_raw_metrics:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model '{model_name}' metadata is missing required_raw_metrics",
        )

    buffer = await build_buffer(asset_id, required_raw_metrics, credentials.credentials)

    result = explain(model_name, buffer, models_dir)
    return result

"""Prediction endpoint: fetch real telemetry, assemble features, run
inference against a saved model."""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
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


async def _run_and_persist_prediction(
    asset_id: str, model_name: str, token: str, db: Session
) -> dict:
    """Load a model, fetch a live buffer, predict, and persist the
    result - shared by GET /predictions/{asset_id} and
    GET /predictions/{asset_id}/attribute so this logic exists in
    exactly one place, not duplicated across both endpoints.

    Raises HTTPException (404/500) on a per-model failure - callers
    that need to run several models and tolerate individual failures
    (attribute_fault below) must catch this themselves, not rely on
    this helper silently swallowing errors.
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

    buffer = await build_buffer(asset_id, required_raw_metrics, token)
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
    """
    return await _run_and_persist_prediction(asset_id, model_name, credentials.credentials, db)


class SkippedModel(BaseModel):
    model_name: str
    reason: str


class ClassifierResult(BaseModel):
    model_name: str
    predicted_label: int
    fault_probability: float
    confidence: str


class AttributedFaultOut(BaseModel):
    """Response for GET /predictions/{asset_id}/attribute.

    Full transparency, not just the winner - all_results lets a caller
    (or a human debugging a confusing alert later) see every classifier
    that was actually compared and its raw probability, not just trust
    a single black-box "the answer is X" verdict.
    """

    asset_id: str
    models_evaluated: list[str]
    models_skipped: list[SkippedModel]
    fault_detected: bool
    attributed_model: str | None
    attributed_fault_probability: float | None
    all_results: list[ClassifierResult]


@router.get("/predictions/{asset_id}/attribute", response_model=AttributedFaultOut)
async def attribute_fault(
    asset_id: str,
    model_names: list[str] = Query(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> AttributedFaultOut:
    """Run several classifier models and attribute the fault to the
    single highest-confidence one, instead of treating "any classifier
    fires" as independently meaningful.

    The real problem this fixes (documented in
    ml/TWO_STAGE_ARCHITECTURE_VALIDATION_LOG.md): on condenser-fouling
    data, liquidline_restriction's classifier fires 93.9% of the time
    and overcharge's fires 89.3% - three classifiers can simultaneously
    claim the same event. Gating (the two-stage anomaly-detector
    architecture) only decides WHETHER classifiers run at all, not
    WHICH ONE to believe once several do - a separate, previously
    unsolved problem, flagged since the validation log as "a distinct
    next task."

    Argmax by fault_probability among classifiers that actually
    predicted a fault (predicted_label == 1) - NOT the global max
    fault_probability across every model run, which would incorrectly
    let a model that correctly said "no fault, 2% probability" win
    against a model that said "fault, 60% probability" just because
    2% > some even-lower confident-fault reading. If zero models
    predict a fault, fault_detected is False and attributed_model is
    None - this is reported honestly, not papered over by picking the
    least-unlikely non-fault result as if it meant something.

    Anomaly-detector models (no predict_proba, e.g. the Isolation
    Forest gatekeeper) passed in model_names are skipped with a clear
    reason, not silently ignored or crashing the whole comparison - the
    argmax concept doesn't apply to them (no fault_probability to
    compare), and mixing detection-gating models into a fault-
    ATTRIBUTION comparison would conflate two different jobs.

    One model failing to load or predict does not fail the whole
    request - skipped with a reason, matching this project's established
    "partial, honest result over all-or-nothing failure" approach (e.g.
    CSV upload's per-row error handling, GET /models skipping malformed
    metadata).
    """
    all_results: list[ClassifierResult] = []
    skipped: list[SkippedModel] = []

    for model_name in model_names:
        try:
            result = await _run_and_persist_prediction(
                asset_id, model_name, credentials.credentials, db
            )
        except HTTPException as err:
            skipped.append(SkippedModel(model_name=model_name, reason=str(err.detail)))
            continue

        if "fault_probability" not in result:
            skipped.append(
                SkippedModel(
                    model_name=model_name,
                    reason="Not a classifier model (no fault_probability) - "
                    "argmax fault attribution only applies to classifiers",
                )
            )
            continue

        all_results.append(
            ClassifierResult(
                model_name=model_name,
                predicted_label=result["predicted_label"],
                fault_probability=result["fault_probability"],
                confidence=result["confidence"],
            )
        )

    fault_candidates = [r for r in all_results if r.predicted_label == 1]
    winner = max(fault_candidates, key=lambda r: r.fault_probability) if fault_candidates else None

    return AttributedFaultOut(
        asset_id=asset_id,
        models_evaluated=[r.model_name for r in all_results],
        models_skipped=skipped,
        fault_detected=winner is not None,
        attributed_model=winner.model_name if winner else None,
        attributed_fault_probability=winner.fault_probability if winner else None,
        all_results=all_results,
    )


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

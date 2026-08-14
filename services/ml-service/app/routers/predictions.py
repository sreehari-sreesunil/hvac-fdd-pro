"""Prediction endpoint: fetch real telemetry, assemble features, run
inference against a saved model."""

import re
import sys
from pathlib import Path
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
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

# Strict allowlist for model_name - it's interpolated directly into a
# file path (models_dir / f"{model_name}.metadata.json") and passed to
# joblib.load() (pickle deserialization under the hood). An unvalidated
# model_name is a real path-traversal-adjacent risk: "../" segments
# could reach outside models_dir, and joblib.load() on an unintended
# file is a genuinely serious outcome, not just a 404. Every real saved
# model name (e.g. "simulated_condenser_fouling") is lowercase letters,
# digits, and underscores only - this pattern is not a guess, it
# matches what train_final_models.py actually produces.
MODEL_NAME_PATTERN = r"^[a-zA-Z0-9_]+$"


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

    # load_model/predict are synchronous, CPU-bound (joblib deserialization,
    # real sklearn/XGBoost inference) - run in a thread pool, not called
    # directly, or they'd block this whole service's single-threaded
    # asyncio event loop for their full duration, serializing every other
    # concurrent request behind them regardless of what that request
    # needed. Real, load-tested finding, not a theoretical concern - see
    # docs/LOAD_TEST_RESULTS.md.
    _, metadata = await run_in_threadpool(load_model, model_name, models_dir)
    required_raw_metrics = metadata.get("required_raw_metrics")
    if not required_raw_metrics:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model '{model_name}' metadata is missing required_raw_metrics",
        )

    buffer = await build_buffer(asset_id, required_raw_metrics, token)
    result = await run_in_threadpool(predict, model_name, buffer, models_dir)

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

    # predict() is imported via sys.path insertion (see docs/TECH_DEBT.md's
    # "ml-service: sys.path import of ml/src instead of a proper package" -
    # a deliberate architectural choice, not addressed here), so mypy can't
    # resolve its real return type and treats it as Any.
    return cast(dict, result)


@router.get("/predictions/{asset_id}")
async def get_prediction(
    asset_id: str,
    model_name: str = Query(..., pattern=MODEL_NAME_PATTERN),
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

    model_names is validated by hand here, not via Query(pattern=...) -
    that constraint applies to the OUTER list type in Pydantic/FastAPI,
    not per-item, and attempting it crashes with an uncaught 500
    (TypeError: Unable to apply constraint 'pattern' to supplied value
    [...] for schema of type 'list') rather than a clean 422 - found by
    actually testing this, not assumed to work the same as the scalar
    str case used by get_prediction/get_prediction_explanation above.
    """
    for model_name in model_names:
        if not re.match(MODEL_NAME_PATTERN, model_name):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid model_name: '{model_name}'",
            )

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
    model_name: str = Query(..., pattern=MODEL_NAME_PATTERN),
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

    # Same blocking-call reasoning as _run_and_persist_prediction above -
    # SHAP explanation is real CPU work too, arguably heavier than a
    # plain predict() call.
    _, metadata = await run_in_threadpool(load_model, model_name, models_dir)
    required_raw_metrics = metadata.get("required_raw_metrics")
    if not required_raw_metrics:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model '{model_name}' metadata is missing required_raw_metrics",
        )

    buffer = await build_buffer(asset_id, required_raw_metrics, credentials.credentials)

    result = await run_in_threadpool(explain, model_name, buffer, models_dir)
    # Same sys.path-import limitation as _run_and_persist_prediction above.
    return cast(dict, result)

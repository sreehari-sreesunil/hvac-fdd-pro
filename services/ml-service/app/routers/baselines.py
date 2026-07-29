"""Per-asset baseline endpoints - fit a frozen reference once, score
future readings against it.

Deliberately NOT continuously recalculated - a continuously-adapting
rolling window "forgets" true normal within its own window length once
it starts seeing fault-affected data (see
ml/PER_ASSET_BASELINE_VALIDATION_LOG.md). Re-fitting (POST again) is a
deliberate action, not automatic.

Uses WEATHER-RESIDUALIZED values, not raw readings - a raw-pressure
validation badly understated the real fault signal (0.29% baseline vs.
just 1.46% at 10% severity, raw, versus 0.29% vs. 36.75%+ residualized).
Weather-regression coefficients are fit ONCE from the reference period
and only ever APPLIED at scoring time, never refit - matching the exact
discipline every classifier/gatekeeper already follows, for the same
reason: live data has no way to know which readings are "baseline" to
refit against.
"""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session

from app.core.deps import security, verify_asset_access
from app.db.session import get_db
from app.models.asset_baseline import AssetBaseline
from app.schemas.baseline import BaselineOut, BaselineScoreOut
from app.services.asset_client import get_metric_name_to_id_map
from app.services.telemetry_client import fetch_metric_readings

router = APIRouter(prefix="/baselines", tags=["baselines"])

WEATHER_METRIC_NAME = "RTU_OA_TEMP"
STAGE_METRIC_NAME = "RTU_STG_STA"
STAGE2_THRESHOLD = 0.9  # matches ml/src/features/filtering.py's stage2_only() exactly
DEFAULT_K_STD = 3.0


async def _fetch_target_and_weather(
    asset_id: str, metric_definition_id: str, token: str
) -> pd.DataFrame:
    """Fetch the target metric + weather + compressor-stage readings,
    inner-joined on recorded_at, then filtered to stage-2 operation only.

    Stage-2 filtering matters here for the same reason
    ml/src/features/build_features.py applies it before any residualization:
    during off/stage-1 operation, a pressure column's relationship to
    outdoor temperature is not the same steady-state relationship the
    weather regression was fit to model, so including those rows (in
    either fitting OR scoring) would compare noise, not signal. An earlier
    live test skipped this and got a misleadingly weak result scoring
    against a non-stage-2 "latest" reading - see
    ml/PER_ASSET_BASELINE_VALIDATION_LOG.md.
    """
    metric_map = await get_metric_name_to_id_map(asset_id, token)
    missing = [m for m in (WEATHER_METRIC_NAME, STAGE_METRIC_NAME) if m not in metric_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This asset is missing required metric(s): {missing}",
        )
    weather_metric_id = metric_map[WEATHER_METRIC_NAME]
    stage_metric_id = metric_map[STAGE_METRIC_NAME]

    target_df = await fetch_metric_readings(asset_id, metric_definition_id, token)
    weather_df = await fetch_metric_readings(asset_id, weather_metric_id, token)
    stage_df = await fetch_metric_readings(asset_id, stage_metric_id, token)

    if target_df.empty or weather_df.empty or stage_df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No telemetry data available yet for this metric, RTU_OA_TEMP, or RTU_STG_STA.",
        )

    merged = target_df.merge(
        weather_df, on="recorded_at", suffixes=("_target", "_weather"), how="inner"
    ).merge(stage_df.rename(columns={"value": "value_stage"}), on="recorded_at", how="inner")
    if merged.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No overlapping timestamps across this metric, RTU_OA_TEMP, and RTU_STG_STA.",
        )

    stage2_only = merged[merged["value_stage"] > STAGE2_THRESHOLD]
    if stage2_only.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No stage-2 (compressor-running) readings found in the available "
                "telemetry window - only off/stage-1 data is present."
            ),
        )
    return stage2_only


@router.post("/{asset_id}", response_model=BaselineOut)
async def fit_baseline(
    asset_id: str,
    metric_definition_id: str = Query(..., description="Metric to baseline"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> AssetBaseline:
    """Fit (or deliberately re-fit) a frozen baseline for one asset+metric.

    KNOWN LIMITATION: uses whatever telemetry is currently available, up
    to telemetry-service's GET /telemetry cap of 500 most recent readings
    - a real constraint on how long a reference period this can currently
    establish, not hidden here. A genuine commissioning-period baseline
    (days/weeks of trusted history) would need telemetry-service's
    pagination extended first - flagged as follow-up work, not solved.
    """
    merged = await _fetch_target_and_weather(
        asset_id, metric_definition_id, credentials.credentials
    )

    weather_values = merged[["value_weather"]]
    target_values = merged["value_target"]

    regression = LinearRegression()
    regression.fit(weather_values, target_values)
    predicted = regression.predict(weather_values)
    residuals = target_values - predicted

    existing = (
        db.query(AssetBaseline)
        .filter(
            AssetBaseline.asset_id == asset_id,
            AssetBaseline.metric_definition_id == metric_definition_id,
        )
        .first()
    )
    if existing:
        db.delete(existing)
        db.flush()

    baseline = AssetBaseline(
        asset_id=asset_id,
        metric_definition_id=metric_definition_id,
        weather_col=WEATHER_METRIC_NAME,
        weather_slope=float(regression.coef_[0]),
        weather_intercept=float(regression.intercept_),
        mean=float(residuals.mean()),
        std=float(residuals.std()),
        n_reference_rows=len(merged),
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


@router.get("/{asset_id}", response_model=BaselineScoreOut)
async def score_against_baseline(
    asset_id: str,
    metric_definition_id: str = Query(...),
    k_std: float = Query(DEFAULT_K_STD, description="Deviation threshold in standard deviations"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> dict:
    """Score the LATEST reading for this asset+metric against its
    previously-fit frozen baseline. 404 if no baseline has been fit yet -
    fitting is a separate, deliberate step (POST first)."""
    baseline = (
        db.query(AssetBaseline)
        .filter(
            AssetBaseline.asset_id == asset_id,
            AssetBaseline.metric_definition_id == metric_definition_id,
        )
        .first()
    )
    if baseline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No baseline has been fit yet for this asset+metric - POST /baselines first.",
        )

    merged = await _fetch_target_and_weather(
        asset_id, metric_definition_id, credentials.credentials
    )
    latest = merged.iloc[-1]

    predicted = baseline.weather_slope * latest["value_weather"] + baseline.weather_intercept
    residual = float(latest["value_target"] - predicted)
    z_score = (residual - baseline.mean) / baseline.std

    return {
        "asset_id": asset_id,
        "metric_definition_id": metric_definition_id,
        "latest_value": float(latest["value_target"]),
        "latest_weather_value": float(latest["value_weather"]),
        "residual": residual,
        "z_score": z_score,
        "is_deviation": abs(z_score) > k_std,
        "baseline_fit_at": baseline.fit_at,
    }

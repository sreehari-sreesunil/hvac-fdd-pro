"""Assemble a live buffer for one asset + model, from real telemetry data.

Ties together asset_client (metric-name -> metric_definition_id lookup)
and telemetry_client (per-metric readings fetch) into the single wide
DataFrame that ml/src/features/live_features.py expects.
"""

import pandas as pd
from fastapi import HTTPException, status

from app.services.asset_client import get_metric_name_to_id_map
from app.services.telemetry_client import fetch_metric_readings


async def build_buffer(asset_id: str, required_raw_metrics: list[str], token: str) -> pd.DataFrame:
    """Fetch and assemble a wide buffer DataFrame for the given asset,
    containing one column per required raw metric plus a Datetime column.

    Raises:
        HTTPException (400): if the asset's asset-type doesn't have a
            metric definition for one or more required metrics - a real,
            actionable error (the asset needs metric mapping configured),
            not a generic 500.
    """
    metric_name_to_id = await get_metric_name_to_id_map(asset_id, token)

    missing = [m for m in required_raw_metrics if m not in metric_name_to_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Asset {asset_id}'s asset type is missing metric definitions for: "
                f"{missing}. Add these metrics to the asset type before requesting "
                "a prediction that requires them."
            ),
        )

    dfs = []
    for metric_name in required_raw_metrics:
        metric_id = metric_name_to_id[metric_name]
        df = await fetch_metric_readings(asset_id, metric_id, token)
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No telemetry data available yet for metric '{metric_name}' on this asset.",
            )
        dfs.append(df.rename(columns={"value": metric_name}))

    buffer = dfs[0]
    for df in dfs[1:]:
        buffer = buffer.merge(df, on="recorded_at", how="inner")

    if buffer.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No overlapping timestamps found across the required metrics for "
                "this asset - each metric's readings must share common timestamps "
                "to build a usable buffer."
            ),
        )

    return (
        buffer.rename(columns={"recorded_at": "Datetime"})
        .sort_values("Datetime")
        .reset_index(drop=True)
    )

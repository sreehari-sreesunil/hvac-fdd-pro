"""Client for fetching recent telemetry readings from telemetry-service.

Forwards the CALLER's own JWT when querying telemetry-service, matching
the service-to-service pattern already established elsewhere in this
project (e.g. telemetry-service's own calls to asset-service) - no
separate service-account auth mechanism.
"""

import httpx
import pandas as pd
from fastapi import HTTPException, status

from app.config import settings


async def fetch_metric_readings(
    asset_id: str, metric_definition_id: str, token: str
) -> pd.DataFrame:
    """Fetch recent readings for one metric, returned as a two-column
    DataFrame (recorded_at, value) sorted ASCENDING by recorded_at.

    Note: GET /telemetry returns at most 500 readings, sorted DESCENDING
    by recorded_at (most recent first) - confirmed by direct testing, not
    assumed from documentation. This function re-sorts to ascending before
    returning, since live_features.py expects ascending-sorted buffers.
    """
    url = f"{settings.telemetry_service_url}/telemetry"
    params = {"asset_id": asset_id, "metric_definition_id": metric_definition_id}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, params=params, headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="telemetry-service unavailable",
            ) from err

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unexpected response from telemetry-service: {response.status_code}",
        )

    data = response.json()
    if not data:
        return pd.DataFrame(columns=["recorded_at", "value"])

    df = pd.DataFrame(data)[["recorded_at", "value"]]
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    return df.sort_values("recorded_at").reset_index(drop=True)

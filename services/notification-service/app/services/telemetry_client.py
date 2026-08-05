"""Client for fetching an asset's ingestion volume from telemetry-service.

Same thin-wrapper shape as asset_client.py - one cross-service HTTP call,
kept out of the router so the router's own logic isn't mixed up with the
mechanics of calling another service.
"""

from datetime import datetime

import httpx
from fastapi import status

from app.config import settings


async def get_asset_ingestion_count(
    asset_id: str, start: datetime, end: datetime, token: str
) -> int:
    """Fetch how many telemetry readings were ingested for an asset in
    [start, end).

    Failures here return 0 rather than raising, deliberately different
    from get_facility_assets' behavior (which raises 503 on failure).
    Reasoning: the asset list is load-bearing (the whole report is
    meaningless without it), but ingestion_count is a supplementary
    "is data flowing" signal per asset - if telemetry-service is briefly
    unreachable while notification-service loops over N assets, failing
    the entire report because one supplementary metric is unavailable
    would be a worse outcome than showing 0 (with 0 being an honest,
    if pessimistic, answer rather than a fabricated one).
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{settings.telemetry_service_url}/telemetry/volume",
                params={
                    "asset_id": asset_id,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError:
            return 0

    if resp.status_code != status.HTTP_200_OK:
        return 0

    return int(resp.json()["count"])

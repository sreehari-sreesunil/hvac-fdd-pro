"""Client for fetching a facility's asset list from asset-service.

Follows the same shape as ml-service's app/services/asset_client.py -
a thin, typed wrapper around one cross-service HTTP call, kept separate
from the router so the router's logic (aggregating alerts) isn't mixed
up with the mechanics of calling another service.
"""

import httpx
from fastapi import HTTPException, status

from app.config import settings


async def get_facility_assets(facility_id: str, token: str) -> list[dict]:
    """Fetch every asset belonging to a facility.

    Returns the raw list of asset dicts from asset-service's AssetOut
    schema (id, facility_id, asset_type_id, name, external_ref,
    created_at) - the report router only needs `id` and `name` from
    this, but returning the full dicts here keeps this client generic
    rather than narrowing it to today's one caller's exact needs.

    Note: this does NOT re-check facility access - by the time a router
    calls this, verify_facility_access has already confirmed the caller
    can see this facility. This call reuses the same bearer token
    purely to fetch data, not to re-authorize.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{settings.asset_service_url}/assets",
                params={"facility_id": facility_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="asset-service unavailable",
            ) from err

    if resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch assets for facility {facility_id} from asset-service",
        )

    return resp.json()

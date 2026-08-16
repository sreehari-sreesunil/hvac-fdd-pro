"""Client for looking up an asset's metric definitions from asset-service.

Resolves canonical metric names (e.g. "RTU_REFG_COND_PRES") to a specific
asset's real metric_definition_id, by fetching the asset (for its
facility_id and asset_type_id), then the facility (for organization_id -
Asset itself doesn't store this directly), then the full asset-types
list for that org, filtering client-side (there is no single-item
GET /asset-types/{id} endpoint - confirmed against the real running API,
not assumed). Deliberately NOT hardcoded per-asset - a hardcoded mapping
would only ever work for one test asset and would drift out of sync with
real asset-service data.

GET /asset-types now requires organization_id as a real query param
(asset-service made asset types org-scoped, no longer a global catalog -
a real multi-tenancy fix). This was a real, live-caught regression: this
function wasn't updated when asset-types became org-scoped, silently
breaking every prediction for every asset on the platform (found via a
real live walkthrough, not a theoretical concern).
"""

import httpx
from fastapi import HTTPException, status

from app.config import settings


async def get_metric_name_to_id_map(asset_id: str, token: str) -> dict[str, str]:
    """Fetch the asset's facility (for organization_id) and asset_type_id,
    then look the type up in that org's asset-types list, and return a
    {metric_name: metric_definition_id} mapping for it."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            asset_resp = await client.get(
                f"{settings.asset_service_url}/assets/{asset_id}", headers=headers
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="asset-service unavailable",
            ) from err
        if asset_resp.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not fetch asset {asset_id} from asset-service",
            )
        asset_data = asset_resp.json()
        asset_type_id = asset_data["asset_type_id"]
        facility_id = asset_data["facility_id"]

        try:
            facility_resp = await client.get(
                f"{settings.asset_service_url}/facilities/{facility_id}", headers=headers
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="asset-service unavailable",
            ) from err
        if facility_resp.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not fetch facility {facility_id} from asset-service",
            )
        organization_id = facility_resp.json()["organization_id"]

        try:
            asset_types_resp = await client.get(
                f"{settings.asset_service_url}/asset-types",
                params={"organization_id": organization_id},
                headers=headers,
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="asset-service unavailable",
            ) from err
    if asset_types_resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not fetch asset types from asset-service",
        )
    all_asset_types = asset_types_resp.json()
    matching_type = next((t for t in all_asset_types if t["id"] == asset_type_id), None)
    if matching_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset type {asset_type_id} not found",
        )
    metric_definitions = matching_type.get("metric_definitions", [])
    return {m["metric_name"]: m["id"] for m in metric_definitions}

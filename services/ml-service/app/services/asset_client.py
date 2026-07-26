"""Client for looking up an asset's metric definitions from asset-service.

Resolves canonical metric names (e.g. "RTU_REFG_COND_PRES") to a specific
asset's real metric_definition_id, by fetching the asset's asset_type_id,
then fetching the full asset-types list and filtering client-side (there
is no single-item GET /asset-types/{id} endpoint - confirmed against the
real running API, not assumed). Deliberately NOT hardcoded per-asset - a
hardcoded mapping would only ever work for one test asset and would drift
out of sync with real asset-service data.
"""

import httpx
from fastapi import HTTPException, status

from app.config import settings


async def get_metric_name_to_id_map(asset_id: str, token: str) -> dict[str, str]:
    """Fetch the asset's asset_type_id, then look it up in the full
    asset-types list, and return a {metric_name: metric_definition_id}
    mapping for that type."""
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

        asset_type_id = asset_resp.json()["asset_type_id"]

        try:
            asset_types_resp = await client.get(
                f"{settings.asset_service_url}/asset-types", headers=headers
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

"""Tool executors - the actual Python functions the LLM's tool calls
run. Each one is deliberately scoped to a SINGLE, already-authorized
asset_id (bound at the chat endpoint level via verify_asset_access, not
chosen by the LLM) - see app/routers/chat.py's module docstring for why
that boundary matters.

Each function forwards the CALLER's own JWT to the other services,
matching the exact service-to-service pattern already established
throughout this project (ml-service's asset_client.py/telemetry_client.py) -
no separate service-account auth needed here, since these calls act on
behalf of a real logged-in user, not a background job.
"""

import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.rag.vector_store import retrieve


async def _get_metric_id(asset_id: str, metric_name: str, token: str) -> str:
    """Resolve a human-readable metric name (e.g. "RTU_REFG_COND_PRES")
    to its real metric_definition_id for this specific asset - mirrors
    ml-service's asset_client.py pattern exactly."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        asset_resp = await client.get(
            f"{settings.asset_service_url}/assets/{asset_id}", headers=headers
        )
        if asset_resp.status_code != status.HTTP_200_OK:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "asset-service unavailable")
        asset_type_id = asset_resp.json()["asset_type_id"]

        types_resp = await client.get(f"{settings.asset_service_url}/asset-types", headers=headers)
        if types_resp.status_code != status.HTTP_200_OK:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "asset-service unavailable")

    matching_type = next((t for t in types_resp.json() if t["id"] == asset_type_id), None)
    if matching_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Asset type {asset_type_id} not found")

    metric_map = {m["metric_name"]: m["id"] for m in matching_type.get("metric_definitions", [])}
    if metric_name not in metric_map:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown metric '{metric_name}'. Available: {list(metric_map.keys())}",
        )
    return metric_map[metric_name]


async def get_telemetry(asset_id: str, metric_name: str, token: str) -> dict:
    """Tool: fetch the latest reading for one metric on this asset."""
    metric_id = await _get_metric_id(asset_id, metric_name, token)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.telemetry_service_url}/telemetry",
            params={"asset_id": asset_id, "metric_definition_id": metric_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != status.HTTP_200_OK:
        return {"error": f"telemetry-service returned {resp.status_code}"}
    readings = resp.json()
    if not readings:
        return {"error": f"No telemetry data available for {metric_name} on this asset"}
    latest = max(readings, key=lambda r: r["recorded_at"])
    return {
        "metric_name": metric_name,
        "latest_value": latest["value"],
        "recorded_at": latest["recorded_at"],
        "n_recent_readings": len(readings),
    }


async def get_baseline_status(asset_id: str, metric_name: str, token: str) -> dict:
    """Tool: check whether this asset+metric is currently deviating from
    its fitted per-asset baseline (see ml/PER_ASSET_BASELINE_VALIDATION_LOG.md
    for what this mechanism actually does and why)."""
    metric_id = await _get_metric_id(asset_id, metric_name, token)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.ml_service_url}/baselines/{asset_id}",
            params={"metric_definition_id": metric_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code == status.HTTP_404_NOT_FOUND:
        return {"error": f"No baseline has been fit yet for {metric_name} on this asset"}
    if resp.status_code != status.HTTP_200_OK:
        return {"error": f"ml-service returned {resp.status_code}"}
    return resp.json()


async def get_alert_history(asset_id: str, token: str, status_filter: str | None = None) -> dict:
    """Tool: fetch recent alerts for this asset, optionally filtered by
    status (open/acknowledged/resolved)."""
    params = {}
    if status_filter:
        params["status"] = status_filter
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.notification_service_url}/alerts/{asset_id}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code != status.HTTP_200_OK:
        return {"error": f"notification-service returned {resp.status_code}"}
    alerts = resp.json()
    return {"count": len(alerts), "alerts": alerts}


async def search_knowledge_base(query: str) -> dict:
    """Tool: search the fault-documentation knowledge base (ASHRAE/DOE/
    LBNL technical literature, see data/source_docs/) for information
    relevant to the query. No asset_id needed - this searches general
    documentation, not live telemetry."""
    results = retrieve(query, n_results=3)
    if not results:
        return {"error": "No relevant documentation found"}
    return {"results": [{"text": r["text"], "source": r["source"]} for r in results]}

"""Tests for app/services/asset_client.py - specifically exercising the
real HTTP call chain (asset -> facility -> asset-types), not mocking it
away at a higher level the way every other ml-service test does.

This gap - zero real coverage of asset_client.py's actual logic (every
other test mocks get_metric_name_to_id_map itself, or mocks
verify_asset_access, neither of which touches this file's real code) -
is exactly why a real, platform-wide breaking regression (asset-service
making GET /asset-types require organization_id, without this client
being updated to pass it) went undetected for a full day despite a
fully green test suite. See docs/ for the live walkthrough that found
it.

Uses asyncio.run(), not pytest-asyncio/anyio markers - neither is a
configured dependency in this service (same situation as
copilot-service's test_diagnose_fault_tool.py, which uses the same
workaround for the same reason).
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.services.asset_client import get_metric_name_to_id_map

ASSET_ID = "asset-1"
FACILITY_ID = "facility-1"
ORG_ID = "org-1"
ASSET_TYPE_ID = "type-1"
TOKEN = "test-token"


def _make_response(status_code: int, json_body: object) -> AsyncMock:
    """A minimal stand-in for httpx.Response - just status_code and a
    sync .json() method, which is all this client actually calls."""
    resp = AsyncMock()
    resp.status_code = status_code
    resp.json = lambda: json_body
    return resp


def test_resolves_metric_names_via_the_real_asset_facility_asset_types_chain():
    """The core, real path: asset -> facility (for organization_id) ->
    asset-types?organization_id=... -> filter by asset_type_id. This is
    the exact chain that was broken - a test that mocked any single
    step away would not have caught the real regression."""

    async def fake_get(url: str, headers=None, params=None):
        if url == "http://asset-service/assets/asset-1":
            return _make_response(
                200, {"id": ASSET_ID, "asset_type_id": ASSET_TYPE_ID, "facility_id": FACILITY_ID}
            )
        if url == "http://asset-service/facilities/facility-1":
            return _make_response(200, {"id": FACILITY_ID, "organization_id": ORG_ID})
        if url == "http://asset-service/asset-types":
            # The real bug: this call MUST include organization_id as a
            # query param, or asset-service would reject it. Asserting
            # on params here, not just the URL, is what actually
            # verifies the fix.
            assert params == {"organization_id": ORG_ID}
            return _make_response(
                200,
                [
                    {
                        "id": ASSET_TYPE_ID,
                        "organization_id": ORG_ID,
                        "name": "RTU",
                        "metric_definitions": [
                            {"metric_name": "RTU_OA_TEMP", "id": "metric-1"},
                            {"metric_name": "RTU_SA_TEMP", "id": "metric-2"},
                        ],
                    }
                ],
            )
        raise AssertionError(f"Unexpected URL requested: {url}")

    with (
        patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=fake_get)),
        patch("app.services.asset_client.settings") as mock_settings,
    ):
        mock_settings.asset_service_url = "http://asset-service"
        result = asyncio.run(get_metric_name_to_id_map(ASSET_ID, TOKEN))

    assert result == {"RTU_OA_TEMP": "metric-1", "RTU_SA_TEMP": "metric-2"}


def test_raises_503_if_asset_types_call_fails():
    """The real bug's actual symptom: asset-types returning a non-200
    (e.g. the 422 asset-service now correctly returns for a missing
    organization_id) surfaces as a clean 503, not a silent empty
    result or an unhandled exception."""

    async def fake_get(url: str, headers=None, params=None):
        if url == "http://asset-service/assets/asset-1":
            return _make_response(
                200, {"id": ASSET_ID, "asset_type_id": ASSET_TYPE_ID, "facility_id": FACILITY_ID}
            )
        if url == "http://asset-service/facilities/facility-1":
            return _make_response(200, {"id": FACILITY_ID, "organization_id": ORG_ID})
        if url == "http://asset-service/asset-types":
            return _make_response(422, {"detail": "organization_id required"})
        raise AssertionError(f"Unexpected URL requested: {url}")

    with (
        patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=fake_get)),
        patch("app.services.asset_client.settings") as mock_settings,
    ):
        mock_settings.asset_service_url = "http://asset-service"
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_metric_name_to_id_map(ASSET_ID, TOKEN))

    assert exc_info.value.status_code == 503
    assert "asset types" in exc_info.value.detail.lower()


def test_raises_503_if_facility_lookup_fails():
    """The facility hop is a real, separate failure point - a facility
    that can't be fetched (e.g. deleted, or asset-service down partway
    through) should fail cleanly too, not silently skip org resolution."""

    async def fake_get(url: str, headers=None, params=None):
        if url == "http://asset-service/assets/asset-1":
            return _make_response(
                200, {"id": ASSET_ID, "asset_type_id": ASSET_TYPE_ID, "facility_id": FACILITY_ID}
            )
        if url == "http://asset-service/facilities/facility-1":
            return _make_response(404, {"detail": "Facility not found"})
        raise AssertionError(f"Unexpected URL requested: {url}")

    with (
        patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=fake_get)),
        patch("app.services.asset_client.settings") as mock_settings,
    ):
        mock_settings.asset_service_url = "http://asset-service"
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_metric_name_to_id_map(ASSET_ID, TOKEN))

    assert exc_info.value.status_code == 503
    assert "facility" in exc_info.value.detail.lower()


def test_raises_404_if_asset_type_not_found_in_the_orgs_list():
    """A real, distinct failure mode from the 503s above: the calls all
    succeed, but the specific asset_type_id genuinely isn't in that
    org's asset-types list (e.g. a stale/deleted type) - reported as a
    404, not conflated with the org's asset-types call itself failing."""

    async def fake_get(url: str, headers=None, params=None):
        if url == "http://asset-service/assets/asset-1":
            return _make_response(
                200, {"id": ASSET_ID, "asset_type_id": ASSET_TYPE_ID, "facility_id": FACILITY_ID}
            )
        if url == "http://asset-service/facilities/facility-1":
            return _make_response(200, {"id": FACILITY_ID, "organization_id": ORG_ID})
        if url == "http://asset-service/asset-types":
            return _make_response(200, [])  # empty - no matching type
        raise AssertionError(f"Unexpected URL requested: {url}")

    with (
        patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=fake_get)),
        patch("app.services.asset_client.settings") as mock_settings,
    ):
        mock_settings.asset_service_url = "http://asset-service"
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_metric_name_to_id_map(ASSET_ID, TOKEN))

    assert exc_info.value.status_code == 404

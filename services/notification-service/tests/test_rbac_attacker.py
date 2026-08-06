"""RBAC attacker-tests for verify_facility_access.

Every existing test for GET /reports/{facility_id} uses
mock_facility_access to bypass this dependency entirely (necessary to
test the report's aggregation logic without a live asset-service) -
which means its actual denial behavior has never been proven by any
test until this file. A bug here would mean a facility's entire alert
history (via the report endpoint this protects) leaking to someone
outside the org.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import verify_facility_access


def _run_verify(mock_status_code: int) -> HTTPException:
    """Calls the real verify_facility_access with a mocked asset-service
    response, returning the HTTPException it raises."""
    fake_response = MagicMock()
    fake_response.status_code = mock_status_code

    mock_client = AsyncMock()
    mock_client.get.return_value = fake_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")

    async def _attempt():
        with pytest.raises(HTTPException) as exc_info:
            await verify_facility_access("some-facility-id", credentials)
        return exc_info.value

    with patch("app.core.deps.httpx.AsyncClient", return_value=mock_client):
        return asyncio.run(_attempt())


def test_denies_when_asset_service_says_not_a_member():
    """The attack: a user who isn't a member of the facility's
    organization requests its report. asset-service's real
    GET /facilities/{id} returns 403 for this case - confirm
    verify_facility_access correctly turns that into a blocked
    request, not silently allowing the report through."""
    error = _run_verify(mock_status_code=403)
    assert error.status_code == 403
    assert error.detail == "Not a member of this facility's organization"


def test_fails_closed_on_an_unexpected_response_from_asset_service():
    """A real security property, not just the expected-case denial:
    if asset-service returns something neither 200, 403, nor 404 (e.g.
    a 500 from an internal error, or a malformed response), this must
    NOT be silently treated as "allowed" - it must fail closed (503),
    the same as an explicit denial. A bug that fell through to "allow"
    on an unrecognized status code would be a real, serious
    vulnerability - this proves that's not what happens here."""
    error = _run_verify(mock_status_code=500)
    assert error.status_code == 503
    assert error.detail == "Unexpected response from asset-service"

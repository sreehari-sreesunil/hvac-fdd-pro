"""RBAC attacker-tests: proving role-gated endpoints actually reject a
caller without the required role, not just that they accept one with
it.

mock_facility_role_denied (conftest.py) has existed since this
service's tests were first written, but until this file, no test ever
actually used it - meaning there was no real proof a viewer-role user
(or anyone outside admin/operator) is genuinely blocked from creating
edge devices or issuing ingestion keys. Only the "happy path" (an
authorized caller succeeds) was ever tested.

Each test here verifies via a direct DB query, not just the response
status code, that nothing was actually persisted despite the denial -
a stronger, more defensive proof than the status code alone, since it
would also catch a future regression where someone reorders the route
body to create data BEFORE checking authorization.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import check_facility_role
from app.db.session import SessionLocal
from app.models.telemetry import EdgeDevice, IngestionKey
from common.roles import Role


def test_register_edge_device_rejects_a_caller_without_admin_or_operator_role(
    client, auth_headers, mock_facility_role_denied
):
    """The attack: a user with e.g. 'viewer' role (or no role in this
    org at all) attempts to register a new edge device. Must be
    blocked, not silently allowed."""
    response = client.post(
        "/edge-devices",
        json={"facility_id": "some-facility-id", "name": "Attacker's Device"},
        headers=auth_headers,
    )
    assert response.status_code == 403

    db = SessionLocal()
    devices = db.query(EdgeDevice).all()
    db.close()
    assert devices == [], "device must not be created when the role check denies the caller"


def test_register_edge_device_succeeds_for_an_authorized_caller(
    client, auth_headers, mock_facility_role_allowed
):
    """Positive control - proves the denial above is a real effect of
    the role check, not a fixture/route bug that would 403 everyone
    regardless of role."""
    response = client.post(
        "/edge-devices",
        json={"facility_id": "some-facility-id", "name": "Legitimate Device"},
        headers=auth_headers,
    )
    assert response.status_code == 201

    db = SessionLocal()
    devices = db.query(EdgeDevice).all()
    db.close()
    assert len(devices) == 1


def test_list_edge_devices_denies_a_caller_with_no_facility_role(
    client, auth_headers, mock_facility_role_denied
):
    """Real gap fixed here: listing devices was previously impossible
    at all (no GET existed), so there was never even a chance for this
    to leak - but now that it exists, it must be role-gated the same
    way every other facility-scoped read is."""
    response = client.get("/edge-devices?facility_id=some-facility-id", headers=auth_headers)
    assert response.status_code == 403


def test_list_edge_devices_returns_devices_for_an_authorized_caller(
    client, auth_headers, mock_facility_role_allowed
):
    """The actual bug this closes: a device registered earlier must be
    visible when listed afterward - previously impossible since the
    endpoint didn't exist, so a registered device could never be seen
    again."""
    create_resp = client.post(
        "/edge-devices",
        json={"facility_id": "some-facility-id", "name": "Real Device"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201

    response = client.get("/edge-devices?facility_id=some-facility-id", headers=auth_headers)
    assert response.status_code == 200
    devices = response.json()
    assert len(devices) == 1
    assert devices[0]["name"] == "Real Device"


def test_issue_ingestion_key_rejects_a_caller_without_admin_or_operator_role(
    client, auth_headers, mock_facility_role_denied
):
    """The attack: a user without admin/operator role attempts to issue
    a new ingestion key for an EXISTING device (e.g. one they can see
    but shouldn't be able to administer). Must be blocked - an issued
    key is a real credential, this is a genuinely serious boundary to
    get right."""
    db = SessionLocal()
    device = EdgeDevice(facility_id="some-facility-id", name="Existing Device")
    db.add(device)
    db.commit()
    device_id = device.id
    db.close()

    response = client.post(f"/edge-devices/{device_id}/keys", headers=auth_headers)
    assert response.status_code == 403

    db = SessionLocal()
    keys = db.query(IngestionKey).filter(IngestionKey.edge_device_id == device_id).all()
    db.close()
    assert keys == [], "no key must be issued when the role check denies the caller"


def test_issue_ingestion_key_succeeds_for_an_authorized_caller(
    client, auth_headers, mock_facility_role_allowed
):
    """Positive control, same reasoning as the edge-device one above."""
    db = SessionLocal()
    device = EdgeDevice(facility_id="some-facility-id", name="Existing Device")
    db.add(device)
    db.commit()
    device_id = device.id
    db.close()

    response = client.post(f"/edge-devices/{device_id}/keys", headers=auth_headers)
    assert response.status_code == 201

    db = SessionLocal()
    keys = db.query(IngestionKey).filter(IngestionKey.edge_device_id == device_id).all()
    db.close()
    assert len(keys) == 1


def test_check_facility_role_denies_when_asset_service_rejects_the_facility_lookup():
    """Exercises a SPECIFIC internal branch of check_facility_role that
    a real live attack (a freshly signed-up user with zero org
    membership, hitting the actual running service) hit directly:
    asset-service's own GET /facilities/{id} returning non-200 (because
    the caller isn't a member of the org that owns this facility)
    blocks the request at THIS layer, before role-comparison logic is
    even reached.

    mock_facility_role_denied (used in the tests above) mocks the whole
    check_facility_role function, so it never actually exercises this
    internal branch - this test closes that real gap, found by noticing
    the live curl attack's error message ("Not authorized for this
    facility") didn't match what the mocked tests were checking for
    ("Requires one of: [...]"), and tracing it to a different, earlier
    denial path in the same function.
    """
    fake_facility_response = MagicMock()
    fake_facility_response.status_code = 403

    mock_client = AsyncMock()
    mock_client.get.return_value = fake_facility_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")

    async def _attempt():
        with pytest.raises(HTTPException) as exc_info:
            await check_facility_role("some-facility-id", credentials, Role.admin, Role.operator)
        return exc_info.value

    with patch("app.core.deps.httpx.AsyncClient", return_value=mock_client):
        error = asyncio.run(_attempt())

    assert error.status_code == 403
    assert error.detail == "Not authorized for this facility"

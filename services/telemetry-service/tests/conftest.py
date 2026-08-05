"""Shared pytest fixtures for telemetry-service tests."""

import os
from unittest.mock import AsyncMock, patch

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AUTH_SERVICE_URL"] = "http://unused-in-tests:8000"
os.environ["ASSET_SERVICE_URL"] = "http://unused-in-tests:8001"

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.deps import verify_asset_access, verify_ingestion_key
from app.db.session import Base, engine
from app.main import app
from app.models.telemetry import EdgeDevice


@pytest.fixture
def client():
    """A TestClient with a fresh database for each test function."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers():
    """A valid JWT for a fake user, signed with the test secret."""
    token = jwt.encode(
        {"sub": "test-user-id", "type": "access", "exp": 9999999999},
        "test-secret-key",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_ingestion_key():
    """Overrides verify_ingestion_key via FastAPI's dependency_overrides —
    the correct mechanism for Depends()-injected dependencies, since
    Depends() captures a direct reference at route-registration time and
    won't see a later unittest.mock.patch on the module namespace."""
    fake_device = EdgeDevice(
        id="test-device-id",
        facility_id="test-facility-id",
        name="Test Device",
    )

    async def _fake_verify_ingestion_key():
        return fake_device

    app.dependency_overrides[verify_ingestion_key] = _fake_verify_ingestion_key
    yield
    app.dependency_overrides.pop(verify_ingestion_key, None)


@pytest.fixture
def mock_facility_role_allowed():
    """Patches check_facility_role to always allow — used for testing
    edge-device/key-management endpoints without real cross-service calls."""
    with patch("app.routers.telemetry.check_facility_role", new_callable=AsyncMock) as mock:
        mock.return_value = "test-user-id"
        yield mock


@pytest.fixture
def mock_facility_role_denied():
    """Patches check_facility_role to always deny."""
    from fastapi import HTTPException, status

    with patch("app.routers.telemetry.check_facility_role", new_callable=AsyncMock) as mock:
        mock.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Requires one of: ['admin', 'operator']"
        )
        yield mock


@pytest.fixture
def mock_asset_access():
    """Overrides verify_asset_access via FastAPI's dependency_overrides -
    the correct mechanism for Depends()-injected dependencies, same
    reasoning as mock_ingestion_key above. This fixture previously used
    unittest.mock.patch, which has no effect on a Depends()-injected
    callable (FastAPI captures a direct reference at route-registration
    time, before a later patch could intercept it) - a real, silent gap
    that went undetected because no test exercised this fixture until
    GET /telemetry/volume's tests did."""
    app.dependency_overrides[verify_asset_access] = lambda: "test-user-id"
    yield
    app.dependency_overrides.pop(verify_asset_access, None)

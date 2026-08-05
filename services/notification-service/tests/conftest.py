"""Shared pytest fixtures for notification-service tests."""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ASSET_SERVICE_URL"] = "http://unused-in-tests:8001"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.deps import verify_asset_access, verify_facility_access
from app.db.session import Base, engine
from app.main import app


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
def mock_facility_access():
    """Overrides verify_facility_access to always succeed, without a real
    HTTP call to asset-service - matches asset-service's own conftest.py
    pattern of overriding the auth dependency at the FastAPI level
    (app.dependency_overrides) rather than mocking httpx directly, which
    is the officially recommended way to test FastAPI dependencies."""
    app.dependency_overrides[verify_facility_access] = lambda: "test-user-id"
    yield
    app.dependency_overrides.pop(verify_facility_access, None)


@pytest.fixture
def mock_asset_access():
    """Same as mock_facility_access, for the per-asset alert endpoints."""
    app.dependency_overrides[verify_asset_access] = lambda: "test-user-id"
    yield
    app.dependency_overrides.pop(verify_asset_access, None)

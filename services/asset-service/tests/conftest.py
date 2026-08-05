"""Shared pytest fixtures for asset-service tests."""

import os
from unittest.mock import AsyncMock, patch

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["AUTH_SERVICE_URL"] = "http://unused-in-tests:8000"

import pytest
from fastapi.testclient import TestClient
from jose import jwt

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
def mock_membership_admin():
    """Patches verify_org_membership everywhere it's imported — no real
    HTTP call to auth-service happens during the test."""
    with (
        patch(
            "app.routers.facilities.verify_org_membership", new_callable=AsyncMock
        ) as mock_facilities,
        patch("app.routers.assets.verify_org_membership", new_callable=AsyncMock) as mock_assets,
    ):
        mock_facilities.return_value = "admin"
        mock_assets.return_value = "admin"
        yield mock_facilities  # existing tests referencing this fixture still get a usable mock object


@pytest.fixture
def mock_membership_denied():
    """Patches verify_org_membership everywhere it's imported, always denying."""
    from fastapi import HTTPException, status

    with (
        patch(
            "app.routers.facilities.verify_org_membership", new_callable=AsyncMock
        ) as mock_facilities,
        patch("app.routers.assets.verify_org_membership", new_callable=AsyncMock) as mock_assets,
    ):
        denial = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization"
        )
        mock_facilities.side_effect = denial
        mock_assets.side_effect = denial
        yield mock_facilities


@pytest.fixture
def auth_headers():
    """A valid JWT for a fake user, signed with the test secret."""
    token = jwt.encode(
        {"sub": "test-user-id", "type": "access", "exp": 9999999999},
        "test-secret-key",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}

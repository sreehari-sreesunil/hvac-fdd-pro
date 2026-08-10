"""Shared pytest fixtures for copilot-service tests.

This is the first test infrastructure this service has had for its
actual API (tests/eval/ already existed, but that's the separate
DeepEval golden-dataset harness, not pytest-based unit/integration
tests). Matches the isolated-DB / mocked-cross-service-call
conventions already established in every other service's conftest.py
this session.
"""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ASSET_SERVICE_URL"] = "http://unused-in-tests:8001"
os.environ["TELEMETRY_SERVICE_URL"] = "http://unused-in-tests:8002"
os.environ["ML_SERVICE_URL"] = "http://unused-in-tests:8003"
os.environ["NOTIFICATION_SERVICE_URL"] = "http://unused-in-tests:8004"
os.environ["GROQ_API_KEY"] = "test-groq-key-unused"

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.deps import verify_asset_access
from app.db.session import Base, engine
from app.main import app


@pytest.fixture
def client():
    """A TestClient with a fresh database for each test function.

    Base.metadata.create_all is required, not optional, even for
    tests that only check schema validation - found via a real
    failure: the "message passes validation" positive-control test
    genuinely reaches the route body (validation succeeds, then it
    tries to persist a Conversation row), so the conversations table
    must actually exist. Matches the pattern already used in every
    other service's conftest.py this session."""
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
def mock_asset_access():
    """Overrides verify_asset_access via FastAPI's dependency_overrides -
    same reasoning as every other service's equivalent fixture this
    session (patch() has no effect on a Depends()-injected callable)."""
    app.dependency_overrides[verify_asset_access] = lambda: "test-user-id"
    yield
    app.dependency_overrides.pop(verify_asset_access, None)

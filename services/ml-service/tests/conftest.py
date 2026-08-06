"""Shared pytest fixtures for ml-service tests.

This is the first test infrastructure this service has had - see
docs/TECH_DEBT.md's "ml-service: automated tests" entry, previously an
accepted, tracked gap. Matches the isolated-DB / mocked-cross-service-
call conventions already established in asset-service/notification-
service/telemetry-service's own conftest.py files.
"""

import os
from pathlib import Path

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ASSET_SERVICE_URL"] = "http://unused-in-tests:8001"
os.environ["TELEMETRY_SERVICE_URL"] = "http://unused-in-tests:8002"
os.environ["AUTH_SERVICE_URL"] = "http://unused-in-tests:8000"
os.environ["NOTIFICATION_SERVICE_URL"] = "http://unused-in-tests:8004"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"
os.environ["SCHEDULER_SERVICE_ACCOUNT_EMAIL"] = "test-scheduler@example.com"
os.environ["SCHEDULER_SERVICE_ACCOUNT_PASSWORD"] = "test-password"
# predictions.py inserts settings.ml_src_dir onto sys.path to import
# from ml/src/ - defaults to "/ml", the Docker volume mount point.
# Inside Docker (e.g. `docker compose exec ml-service poetry run
# pytest`), /ml genuinely exists and must be left alone - overriding it
# would break the exact case this override was meant to help.
# Only outside Docker (e.g. running `poetry run pytest` directly on a
# local checkout, where /app doesn't exist and /ml doesn't either) does
# this need to point at the real local ml/ directory instead, three
# levels up from services/ml-service/tests/.
if not Path("/ml").exists():
    os.environ["ML_SRC_DIR"] = str(Path(__file__).resolve().parents[3] / "ml")

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.deps import verify_asset_access
from app.main import app


@pytest.fixture
def client():
    """A TestClient for the app. ml-service has no per-request DB
    session dependency of its own to override here (unlike the other
    services) - its endpoints read from models_dir on disk and call
    out to other services, rather than owning a SQLAlchemy model."""
    with TestClient(app) as c:
        yield c


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
    same reasoning as every other service's equivalent fixture (patch()
    has no effect on a Depends()-injected callable)."""
    app.dependency_overrides[verify_asset_access] = lambda: "test-user-id"
    yield
    app.dependency_overrides.pop(verify_asset_access, None)

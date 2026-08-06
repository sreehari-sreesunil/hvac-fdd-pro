"""Shared pytest fixtures for auth-service tests."""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.core.limiter import limiter
from app.db.session import Base, engine
from app.main import app


@pytest.fixture
def client():
    """A TestClient with a fresh database for each test function."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clears slowapi's in-memory counters before each test.

    The Limiter instance (app/core/limiter.py) is a module-level
    singleton, created once at import time and shared across the whole
    test session - without this reset, requests from an earlier rate-
    limit test would still count toward the limit in a later,
    unrelated test (e.g. a normal login test could start already
    "used up" by a previous test's requests), a real source of
    confusing, order-dependent test flakiness.
    """
    limiter.reset()

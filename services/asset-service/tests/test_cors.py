"""Tests for CORS origin restriction - previously a wildcard ("*"),
flagged as a real gap by this project's input validation/security
audit before any real deployment (a wildcard means literally any
website can make authenticated cross-origin requests against this API
from a user's browser).
"""


def test_cors_allows_the_configured_origin(client):
    response = client.get("/asset-types", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_omits_the_header_for_an_unlisted_origin(client):
    """A simple (non-preflight) request from a disallowed origin still
    reaches the route (the browser enforces the actual block client-
    side), but the response must not carry an
    Access-Control-Allow-Origin header matching it."""
    response = client.get("/asset-types", headers={"Origin": "http://evil.example.com"})
    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_cors_preflight_rejects_an_unlisted_origin(client):
    """Preflight (OPTIONS) requests are where CORS restriction is
    actually enforced server-side, not just left to the browser -
    Starlette's CORSMiddleware returns 400 for a disallowed origin's
    preflight, confirmed directly against this real behavior rather
    than assumed."""
    response = client.options(
        "/asset-types",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400


def test_cors_preflight_allows_the_configured_origin(client):
    response = client.options(
        "/asset-types",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200

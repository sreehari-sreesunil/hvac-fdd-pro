"""Tests for rate limiting on auth-service's public endpoints.

reset_rate_limiter (conftest.py, autouse) clears counters before each
test, so these tests are independent of each other and of execution
order.
"""


def test_login_allows_requests_up_to_the_limit(client):
    """5 requests/minute is the configured limit - the 5th request must
    still succeed (as a real 401 for wrong credentials, not a 429) -
    proves the limiter doesn't fire early."""
    for _ in range(5):
        response = client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
        assert response.status_code == 401, "expected a real auth failure, not a rate limit"


def test_login_blocks_the_request_after_the_limit(client):
    """The 6th request within the same window must be rejected with 429,
    not processed as a normal (failed) login attempt."""
    for _ in range(5):
        client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})

    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert response.status_code == 429


def test_signup_has_its_own_limit_independent_of_login(client):
    """signup (3/minute) and login (5/minute) must be tracked separately -
    exhausting login's budget must not affect signup's, and vice versa."""
    for _ in range(5):
        client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})

    # login is now rate-limited, but signup should still have its own,
    # untouched budget
    response = client.post(
        "/auth/signup",
        json={"email": "fresh@example.com", "password": "supersecret123"},
    )
    assert response.status_code == 201


def test_signup_blocks_after_its_own_limit(client):
    """signup's limit (3/minute) is lower than login's - confirms it's
    actually enforced with its own configured number, not accidentally
    inheriting login's higher limit."""
    for i in range(3):
        response = client.post(
            "/auth/signup",
            json={"email": f"user{i}@example.com", "password": "supersecret123"},
        )
        assert response.status_code == 201

    response = client.post(
        "/auth/signup",
        json={"email": "one-too-many@example.com", "password": "supersecret123"},
    )
    assert response.status_code == 429


def test_refresh_has_a_higher_limit_than_login(client):
    """refresh (20/minute) is deliberately more generous than login -
    prove it tolerates more requests than login's limit would allow,
    using invalid tokens (401s) so the volume itself is the only thing
    under test, not real token validity."""
    for _ in range(10):
        response = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
        assert response.status_code == 401, "expected a real auth failure, not a rate limit"

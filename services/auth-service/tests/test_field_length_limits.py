"""Tests for max_length input validation on auth-service's schemas -
a real, systemic finding from this project's input validation audit
(previously zero max_length constraints existed anywhere in this
codebase).
"""


def test_signup_rejects_a_password_over_72_bytes(client):
    """max_length=72 is not arbitrary - bcrypt silently truncates
    anything longer, so this must be enforced, not just documented."""
    response = client.post(
        "/auth/signup",
        json={"email": "longpw@example.com", "password": "a" * 73},
    )
    assert response.status_code == 422


def test_signup_accepts_a_password_at_exactly_72_bytes(client):
    response = client.post(
        "/auth/signup",
        json={"email": "exactpw@example.com", "password": "a" * 72},
    )
    assert response.status_code == 201


def test_signup_rejects_a_full_name_over_255_characters(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "longname@example.com",
            "password": "supersecret123",
            "full_name": "a" * 256,
        },
    )
    assert response.status_code == 422


def test_login_rejects_a_password_over_72_bytes(client):
    """Same reasoning as signup - an unbounded password on every login
    attempt is a real (if smaller) resource-exhaustion consideration."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "a" * 73},
    )
    assert response.status_code == 422


def test_create_organization_rejects_a_name_over_255_characters(client):
    client.post("/auth/signup", json={"email": "orgtest@example.com", "password": "supersecret123"})
    login_resp = client.post(
        "/auth/login", json={"email": "orgtest@example.com", "password": "supersecret123"}
    )
    token = login_resp.json()["access_token"]

    response = client.post(
        "/organizations",
        json={"name": "a" * 256},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422

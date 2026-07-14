"""End-to-end tests for the auth-service signup/login/organizations flow."""


def test_signup_creates_user(client):
    """A new user can sign up and receives back their profile (no password)."""
    response = client.post(
        "/auth/signup",
        json={
            "email": "engineer@example.com",
            "password": "supersecret123",
            "full_name": "Test Engineer",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "engineer@example.com"
    assert "hashed_password" not in body  # UserOut must never leak the hash


def test_signup_rejects_duplicate_email(client):
    """Signing up twice with the same email is rejected."""
    payload = {"email": "dupe@example.com", "password": "supersecret123"}
    first = client.post("/auth/signup", json=payload)
    second = client.post("/auth/signup", json=payload)
    assert first.status_code == 201
    assert second.status_code == 400


def test_login_with_correct_credentials_returns_tokens(client):
    """A registered user can log in and receives an access + refresh token."""
    client.post(
        "/auth/signup", json={"email": "engineer@example.com", "password": "supersecret123"}
    )
    response = client.post(
        "/auth/login", json={"email": "engineer@example.com", "password": "supersecret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_with_wrong_password_is_rejected(client):
    """A wrong password returns 401, not a hint about which part was wrong."""
    client.post(
        "/auth/signup", json={"email": "engineer@example.com", "password": "supersecret123"}
    )
    response = client.post(
        "/auth/login", json={"email": "engineer@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_organizations_endpoint_requires_auth(client):
    """Calling /organizations with no token at all is rejected."""
    response = client.post("/organizations", json={"name": "Acme Co"})
    assert response.status_code == 401  # HTTPBearer's own rejection for a missing header


def test_authenticated_user_can_create_and_list_organization(client):
    """Full flow: signup -> login -> create org -> creator sees it, with admin role."""
    client.post(
        "/auth/signup", json={"email": "engineer@example.com", "password": "supersecret123"}
    )
    login_resp = client.post(
        "/auth/login", json={"email": "engineer@example.com", "password": "supersecret123"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/organizations", json={"name": "Acme Facilities Co"}, headers=headers
    )
    assert create_resp.status_code == 201
    org_id = create_resp.json()["id"]

    list_resp = client.get("/organizations", headers=headers)
    assert list_resp.status_code == 200
    orgs = list_resp.json()
    matching = next(org for org in orgs if org["id"] == org_id)
    assert matching["role"] == "admin"  # creator is always admin


def test_second_user_does_not_see_first_users_organization(client):
    """RBAC/tenancy check: a user who never joined an org shouldn't see it."""
    # User A creates an org
    client.post("/auth/signup", json={"email": "usera@example.com", "password": "supersecret123"})
    login_a = client.post(
        "/auth/login", json={"email": "usera@example.com", "password": "supersecret123"}
    )
    token_a = login_a.json()["access_token"]
    client.post(
        "/organizations",
        json={"name": "User A's Org"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # User B is a completely separate account
    client.post("/auth/signup", json={"email": "userb@example.com", "password": "supersecret123"})
    login_b = client.post(
        "/auth/login", json={"email": "userb@example.com", "password": "supersecret123"}
    )
    token_b = login_b.json()["access_token"]

    list_resp_b = client.get("/organizations", headers={"Authorization": f"Bearer {token_b}"})
    assert list_resp_b.status_code == 200
    assert list_resp_b.json() == []  # User B belongs to nothing


def test_admin_can_invite_existing_user_to_org(client):
    """An org admin can add an existing user as a member with a given role."""

    # Signup admin
    client.post(
        "/auth/signup",
        json={
            "email": "admin@example.com",
            "password": "Password123!",
            "full_name": "Admin User",
        },
    )

    # Login admin
    login_response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Password123!",
        },
    )

    admin_token = login_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create organization
    org_response = client.post(
        "/organizations",
        json={"name": "Test Organization"},
        headers=admin_headers,
    )

    assert org_response.status_code == 201
    org_id = org_response.json()["id"]

    # Signup second user
    client.post(
        "/auth/signup",
        json={
            "email": "operator@example.com",
            "password": "Password123!",
            "full_name": "Operator User",
        },
    )

    # Invite second user
    invite_response = client.post(
        f"/organizations/{org_id}/invite",
        json={
            "email": "operator@example.com",
            "role": "operator",
        },
        headers=admin_headers,
    )

    assert invite_response.status_code == 201

    body = invite_response.json()
    assert body["user_id"] is not None
    assert body["role"] == "operator"


def test_non_admin_cannot_invite(client):
    """A viewer/operator (or non-member) cannot invite others."""

    # Signup admin
    client.post(
        "/auth/signup",
        json={
            "email": "admin@example.com",
            "password": "Password123!",
            "full_name": "Admin User",
        },
    )

    # Login admin
    login_response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Password123!",
        },
    )

    admin_token = login_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create organization
    org_response = client.post(
        "/organizations",
        json={"name": "Test Organization"},
        headers=admin_headers,
    )

    assert org_response.status_code == 201
    org_id = org_response.json()["id"]

    # Signup second user
    client.post(
        "/auth/signup",
        json={
            "email": "user@example.com",
            "password": "Password123!",
            "full_name": "Regular User",
        },
    )

    # Login second user
    login_response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "Password123!",
        },
    )

    user_token = login_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Attempt to invite another user
    invite_response = client.post(
        f"/organizations/{org_id}/invite",
        json={
            "email": "someone@example.com",
            "role": "operator",
        },
        headers=user_headers,
    )

    assert invite_response.status_code == 403

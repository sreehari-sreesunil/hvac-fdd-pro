"""Tests for facility endpoints. Cross-service membership checks are
mocked — see conftest.py — so these tests run without a live auth-service."""


def test_create_facility_succeeds_for_a_member(client, mock_membership_admin, auth_headers):
    """A caller whose membership check passes can create a facility."""
    response = client.post(
        "/facilities",
        json={
            "organization_id": "some-org-id",
            "name": "Downtown Office Tower",
            "address": "123 Main St",
            "timezone": "America/New_York",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Downtown Office Tower"
    assert body["organization_id"] == "some-org-id"

    # Confirm verify_org_membership was actually called with the right org
    mock_membership_admin.assert_called_once()
    called_org_id = mock_membership_admin.call_args[0][0]
    assert called_org_id == "some-org-id"


def test_create_facility_rejected_for_non_member(client, mock_membership_denied, auth_headers):
    """A caller whose membership check fails cannot create a facility."""
    response = client.post(
        "/facilities",
        json={"organization_id": "some-org-id", "name": "Should Not Exist"},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_list_facilities_returns_only_that_orgs_facilities(
    client, mock_membership_admin, auth_headers
):
    """Listing facilities is scoped to the requested organization."""
    client.post(
        "/facilities",
        json={"organization_id": "org-a", "name": "Facility A"},
        headers=auth_headers,
    )
    client.post(
        "/facilities",
        json={"organization_id": "org-b", "name": "Facility B"},
        headers=auth_headers,
    )

    response = client.get(
        "/facilities?organization_id=org-a",
        headers=auth_headers,
    )
    assert response.status_code == 200
    names = [f["name"] for f in response.json()]
    assert names == ["Facility A"]

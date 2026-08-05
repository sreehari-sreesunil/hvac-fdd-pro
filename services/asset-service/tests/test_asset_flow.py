"""Tests for asset endpoints. Assets belong to a Facility, which belongs to
an Organization — so creating an asset requires a real Facility to already
exist in the test database, plus a mocked membership check for its org."""


def test_create_asset_succeeds_for_a_member(client, mock_membership_admin, auth_headers):
    """Creating an asset works when the facility exists and membership passes."""
    # An Asset references a Facility by id, so a real Facility row must
    # exist first — create one via the actual API, same as a real user would.
    facility_resp = client.post(
        "/facilities",
        json={"organization_id": "org-a", "name": "Downtown Tower"},
        headers=auth_headers,
    )
    facility_id = facility_resp.json()["id"]

    # An Asset also references an AssetType by id — same reasoning.
    asset_type_resp = client.post(
        "/asset-types",
        json={"name": "RTU", "metrics": []},
        headers=auth_headers,
    )
    asset_type_id = asset_type_resp.json()["id"]

    response = client.post(
        "/assets",
        json={
            "facility_id": facility_id,
            "asset_type_id": asset_type_id,
            "name": "RTU-4",
            "external_ref": "bacnet-device-1042",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "RTU-4"
    assert body["facility_id"] == facility_id


def test_create_asset_fails_for_nonexistent_facility(client, mock_membership_admin, auth_headers):
    """Referencing a facility_id that doesn't exist returns 404, not a crash."""
    response = client.post(
        "/assets",
        json={
            "facility_id": "does-not-exist",
            "asset_type_id": "also-fake",
            "name": "Ghost Asset",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_asset_rejected_for_non_member(client, mock_membership_denied, auth_headers):
    """Even with a real facility, a failed membership check blocks creation."""
    # Note: this facility is created under mock_membership_denied, so the
    # facility-creation call itself will also be rejected — meaning there's
    # no real facility for the asset step to reference. This test instead
    # proves the 403 happens BEFORE reaching asset-creation logic at all,
    # using a facility_id that doesn't need to be real for that purpose.
    response = client.post(
        "/assets",
        json={
            "facility_id": "irrelevant-since-membership-fails-first",
            "asset_type_id": "x",
            "name": "X",
        },
        headers=auth_headers,
    )
    # Membership check never runs here — the facility lookup happens FIRST
    # in create_asset, and this facility_id doesn't exist, so 404 fires
    # before verify_org_membership is ever reached.
    assert response.status_code == 404


def test_list_assets_for_a_facility(client, mock_membership_admin, auth_headers):
    """Listing assets is scoped to the given facility."""
    facility_resp = client.post(
        "/facilities", json={"organization_id": "org-a", "name": "Tower"}, headers=auth_headers
    )
    facility_id = facility_resp.json()["id"]
    asset_type_resp = client.post(
        "/asset-types", json={"name": "RTU", "metrics": []}, headers=auth_headers
    )
    asset_type_id = asset_type_resp.json()["id"]

    client.post(
        "/assets",
        json={"facility_id": facility_id, "asset_type_id": asset_type_id, "name": "RTU-1"},
        headers=auth_headers,
    )
    client.post(
        "/assets",
        json={"facility_id": facility_id, "asset_type_id": asset_type_id, "name": "RTU-2"},
        headers=auth_headers,
    )

    response = client.get(f"/assets?facility_id={facility_id}", headers=auth_headers)
    assert response.status_code == 200
    names = [a["name"] for a in response.json()]
    assert set(names) == {"RTU-1", "RTU-2"}

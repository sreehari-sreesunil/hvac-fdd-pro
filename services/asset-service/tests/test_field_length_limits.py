"""Tests for max_length input validation on asset-service's schemas -
part of this project's input validation audit (previously zero
max_length constraints existed anywhere in this codebase).
"""


def test_create_facility_rejects_a_name_over_255_characters(
    client, auth_headers, mock_membership_admin
):
    response = client.post(
        "/facilities",
        json={"organization_id": "org-1", "name": "a" * 256},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_facility_rejects_an_address_over_500_characters(
    client, auth_headers, mock_membership_admin
):
    response = client.post(
        "/facilities",
        json={"organization_id": "org-1", "name": "Real Facility", "address": "a" * 501},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_asset_type_rejects_a_name_over_255_characters(client, auth_headers):
    response = client.post(
        "/asset-types",
        json={"name": "a" * 256},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_asset_type_rejects_a_description_over_2000_characters(client, auth_headers):
    response = client.post(
        "/asset-types",
        json={"name": "Real Asset Type", "description": "a" * 2001},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_add_metric_definition_rejects_a_metric_name_over_255_characters(client, auth_headers):
    create_resp = client.post("/asset-types", json={"name": "RTU"}, headers=auth_headers)
    asset_type_id = create_resp.json()["id"]

    response = client.post(
        f"/asset-types/{asset_type_id}/metrics",
        json={"metric_name": "a" * 256, "display_name": "Some Metric"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_asset_type_still_works_normally_under_the_limit(client, auth_headers):
    """Positive control - proves the limits above aren't accidentally
    rejecting normal, well-formed input."""
    response = client.post(
        "/asset-types",
        json={"name": "Normal RTU", "description": "A perfectly reasonable description."},
        headers=auth_headers,
    )
    assert response.status_code == 201

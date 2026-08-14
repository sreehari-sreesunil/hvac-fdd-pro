"""Tests for POST /asset-types/{asset_type_id}/metrics."""


def _create_asset_type(client, auth_headers, name="RTU", metrics=None, organization_id="org-a"):
    response = client.post(
        "/asset-types",
        json={"organization_id": organization_id, "name": name, "metrics": metrics or []},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


def test_add_metric_definition_to_an_existing_asset_type(
    client, mock_membership_admin, auth_headers
):
    """The core case this endpoint exists for: a metric can be added
    after the asset type already exists, not just at creation time."""
    asset_type = _create_asset_type(client, auth_headers, name="RTU")

    response = client.post(
        f"/asset-types/{asset_type['id']}/metrics",
        json={
            "metric_name": "RTU_OA_TEMP",
            "display_name": "Outdoor Air Temp",
            "unit": "°F",
            "chart_type": "line",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["metric_name"] == "RTU_OA_TEMP"
    assert body["asset_type_id"] == asset_type["id"]

    # Confirm it's actually attached, not just returned in isolation.
    get_resp = client.get("/asset-types?organization_id=org-a", headers=auth_headers)
    rtu = next(a for a in get_resp.json() if a["id"] == asset_type["id"])
    metric_names = [m["metric_name"] for m in rtu["metric_definitions"]]
    assert "RTU_OA_TEMP" in metric_names


def test_add_metric_definition_to_nonexistent_asset_type_returns_404(
    client, mock_membership_admin, auth_headers
):
    response = client.post(
        "/asset-types/does-not-exist/metrics",
        json={"metric_name": "RTU_OA_TEMP", "display_name": "Outdoor Air Temp"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_add_duplicate_metric_name_to_same_asset_type_returns_409(
    client, mock_membership_admin, auth_headers
):
    """metric_name must be unique within an asset type - a duplicate
    would make metric-mapping genuinely ambiguous."""
    asset_type = _create_asset_type(
        client,
        auth_headers,
        name="RTU",
        metrics=[{"metric_name": "RTU_OA_TEMP", "display_name": "Outdoor Air Temp"}],
    )

    response = client.post(
        f"/asset-types/{asset_type['id']}/metrics",
        json={"metric_name": "RTU_OA_TEMP", "display_name": "A different display name"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_same_metric_name_is_fine_on_different_asset_types(
    client, mock_membership_admin, auth_headers
):
    """The uniqueness constraint is scoped per asset type, not global -
    two different asset types (e.g. RTU and AHU) can each legitimately
    have their own RTU_OA_TEMP-equivalent metric."""
    rtu = _create_asset_type(client, auth_headers, name="RTU")
    ahu = _create_asset_type(client, auth_headers, name="AHU")

    resp1 = client.post(
        f"/asset-types/{rtu['id']}/metrics",
        json={"metric_name": "OA_TEMP", "display_name": "Outdoor Air Temp"},
        headers=auth_headers,
    )
    resp2 = client.post(
        f"/asset-types/{ahu['id']}/metrics",
        json={"metric_name": "OA_TEMP", "display_name": "Outdoor Air Temp"},
        headers=auth_headers,
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201


def test_add_metric_definition_requires_auth(client, mock_membership_admin, auth_headers):
    asset_type = _create_asset_type(client, auth_headers, name="RTU")

    response = client.post(
        f"/asset-types/{asset_type['id']}/metrics",
        json={"metric_name": "RTU_OA_TEMP", "display_name": "Outdoor Air Temp"},
    )
    assert response.status_code in (401, 403)

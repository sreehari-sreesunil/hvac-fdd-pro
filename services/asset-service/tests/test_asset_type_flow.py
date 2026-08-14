"""Tests for asset type endpoints. Org-scoped, same as facilities - see
app/models/asset.py's AssetType docstring for why this changed from the
original global-catalog design (a real live walkthrough with a genuinely
new organization surfaced that any org could see and use every other
org's asset types)."""

from unittest.mock import AsyncMock, patch


def test_create_asset_type_with_metrics(client, mock_membership_admin, auth_headers):
    """Creating an asset type returns it with its metric definitions attached."""
    response = client.post(
        "/asset-types",
        json={
            "organization_id": "org-a",
            "name": "RTU",
            "description": "Rooftop Unit",
            "metrics": [
                {
                    "metric_name": "supply_air_temp",
                    "display_name": "Supply Air Temp",
                    "unit": "°C",
                    "chart_type": "line",
                },
                {
                    "metric_name": "return_air_temp",
                    "display_name": "Return Air Temp",
                    "unit": "°C",
                    "chart_type": "line",
                },
                {
                    "metric_name": "compressor_current",
                    "display_name": "Compressor Current",
                    "unit": "A",
                    "chart_type": "gauge",
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "RTU"
    assert body["organization_id"] == "org-a"
    assert len(body["metric_definitions"]) == 3
    metric_names = [m["metric_name"] for m in body["metric_definitions"]]
    assert "supply_air_temp" in metric_names


def test_create_asset_type_without_metrics(client, mock_membership_admin, auth_headers):
    """metrics defaults to an empty list — an asset type can exist with none yet."""
    response = client.post(
        "/asset-types",
        json={"organization_id": "org-a", "name": "Chiller", "description": "Water chiller"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["metric_definitions"] == []


def test_list_asset_types_returns_only_that_orgs_types(client, mock_membership_admin, auth_headers):
    """Listing asset types is scoped to the requested organization - the
    real bug this whole change fixes: a brand-new org should never see
    another org's asset types."""
    client.post(
        "/asset-types",
        json={"organization_id": "org-a", "name": "RTU", "metrics": []},
        headers=auth_headers,
    )
    client.post(
        "/asset-types",
        json={"organization_id": "org-b", "name": "Chiller", "metrics": []},
        headers=auth_headers,
    )

    response = client.get("/asset-types?organization_id=org-a", headers=auth_headers)
    assert response.status_code == 200
    names = [a["name"] for a in response.json()]
    assert names == ["RTU"]


def test_two_orgs_can_each_have_an_asset_type_with_the_same_name(
    client, mock_membership_admin, auth_headers
):
    """The old global-uniqueness constraint on `name` alone would have
    blocked this - uniqueness is now per-organization."""
    resp_a = client.post(
        "/asset-types",
        json={"organization_id": "org-a", "name": "RTU", "metrics": []},
        headers=auth_headers,
    )
    resp_b = client.post(
        "/asset-types",
        json={"organization_id": "org-b", "name": "RTU", "metrics": []},
        headers=auth_headers,
    )
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    assert resp_a.json()["id"] != resp_b.json()["id"]


def test_create_asset_type_rejected_for_non_member(client, mock_membership_denied, auth_headers):
    """A caller who isn't a member of the target org can't create an
    asset type there."""
    response = client.post(
        "/asset-types",
        json={"organization_id": "org-a", "name": "RTU", "metrics": []},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_list_asset_types_rejected_for_non_member(client, mock_membership_denied, auth_headers):
    response = client.get("/asset-types?organization_id=org-a", headers=auth_headers)
    assert response.status_code == 403


def test_add_metric_definition_rejected_for_non_org_member(client, auth_headers):
    """Adding a metric to an existing asset type is checked against THAT
    asset type's own org (fetch-then-verify, same pattern as
    get_facility) - not skipped, not assumed from the caller's own
    claimed org. Create as an admitted member, then deny membership for
    the follow-up call against the same, now-real asset type."""
    with patch(
        "app.routers.asset_types.verify_org_membership", new_callable=AsyncMock
    ) as mock_verify:
        mock_verify.return_value = "admin"
        create_resp = client.post(
            "/asset-types",
            json={"organization_id": "org-a", "name": "RTU", "metrics": []},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        asset_type_id = create_resp.json()["id"]

        from fastapi import HTTPException, status

        mock_verify.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization"
        )
        add_metric_resp = client.post(
            f"/asset-types/{asset_type_id}/metrics",
            json={"metric_name": "supply_air_temp", "display_name": "Supply Air Temp"},
            headers=auth_headers,
        )
        assert add_metric_resp.status_code == 403


def test_create_asset_type_requires_auth(client):
    """No Authorization header at all is rejected."""
    response = client.post(
        "/asset-types", json={"organization_id": "org-a", "name": "RTU", "metrics": []}
    )
    assert response.status_code in (401, 403)

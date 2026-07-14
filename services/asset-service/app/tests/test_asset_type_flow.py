"""Tests for asset type endpoints. No membership mocking needed — asset
types are global, not org-scoped, so only auth_headers is required."""


def test_create_asset_type_with_metrics(client, auth_headers):
    """Creating an asset type returns it with its metric definitions attached."""
    response = client.post(
        "/asset-types",
        json={
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
    assert len(body["metric_definitions"]) == 3
    metric_names = [m["metric_name"] for m in body["metric_definitions"]]
    assert "supply_air_temp" in metric_names


def test_create_asset_type_without_metrics(client, auth_headers):
    """metrics defaults to an empty list — an asset type can exist with none yet."""
    response = client.post(
        "/asset-types",
        json={"name": "Chiller", "description": "Water chiller"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["metric_definitions"] == []


def test_list_asset_types_returns_created_types(client, auth_headers):
    """Listing returns every asset type created so far."""
    client.post("/asset-types", json={"name": "RTU", "metrics": []}, headers=auth_headers)
    client.post("/asset-types", json={"name": "Chiller", "metrics": []}, headers=auth_headers)

    response = client.get("/asset-types", headers=auth_headers)
    assert response.status_code == 200
    names = [a["name"] for a in response.json()]
    assert "RTU" in names
    assert "Chiller" in names


def test_create_asset_type_requires_auth(client):
    """No Authorization header at all is rejected."""
    response = client.post("/asset-types", json={"name": "RTU", "metrics": []})
    assert response.status_code in (401, 403)

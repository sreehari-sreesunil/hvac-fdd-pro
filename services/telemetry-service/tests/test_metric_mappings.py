"""Tests for GET /metric-mappings."""


def _create_mapping(client, auth_headers, asset_id, external_key, metric_definition_id):
    resp = client.post(
        "/metric-mappings",
        headers=auth_headers,
        json={
            "asset_id": asset_id,
            "external_key": external_key,
            "metric_definition_id": metric_definition_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_list_metric_mappings_returns_existing_mappings_for_the_asset(
    client, auth_headers, mock_asset_access
):
    """The core case: mappings already created for this asset are
    returned."""
    _create_mapping(client, auth_headers, "asset-1", "SAT", "metric-def-supply-temp")
    _create_mapping(client, auth_headers, "asset-1", "RAT", "metric-def-return-temp")

    response = client.get(
        "/metric-mappings",
        params={"asset_id": "asset-1"},
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    external_keys = {m["external_key"] for m in body}
    assert external_keys == {"SAT", "RAT"}


def test_list_metric_mappings_only_returns_the_requested_asset(
    client, auth_headers, mock_asset_access
):
    """A mapping on a different asset must not leak into this asset's
    list - proves the query filters on asset_id, not just returning
    every mapping in the table."""
    _create_mapping(client, auth_headers, "asset-1", "SAT", "metric-def-1")
    _create_mapping(client, auth_headers, "asset-2", "SAT", "metric-def-1")

    response = client.get(
        "/metric-mappings",
        params={"asset_id": "asset-1"},
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["asset_id"] == "asset-1"


def test_list_metric_mappings_with_none_returns_empty_list_not_an_error(client, mock_asset_access):
    """An asset with zero mappings yet (e.g. right after being created)
    is a real, valid state - not a failure."""
    response = client.get(
        "/metric-mappings",
        params={"asset_id": "asset-with-no-mappings"},
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 200
    assert response.json() == []

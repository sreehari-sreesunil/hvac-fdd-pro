"""Tests for GET /telemetry/volume."""


def _ingest(client, asset_id, external_key, value, recorded_at):
    resp = client.post(
        "/telemetry",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "asset_id": asset_id,
            "external_key": external_key,
            "value": value,
            "recorded_at": recorded_at,
        },
    )
    assert resp.status_code == 201
    return resp


def test_volume_counts_only_readings_in_the_date_range(
    client, mock_ingestion_key, mock_asset_access
):
    """Two readings inside the window, one outside - only the two
    inside should be counted."""
    _ingest(client, "asset-1", "SAT", 70.0, "2026-08-01T00:00:00Z")
    _ingest(client, "asset-1", "SAT", 71.0, "2026-08-03T00:00:00Z")
    _ingest(client, "asset-1", "SAT", 72.0, "2026-07-01T00:00:00Z")  # outside

    response = client.get(
        "/telemetry/volume",
        params={
            "asset_id": "asset-1",
            "start_date": "2026-08-01T00:00:00",
            "end_date": "2026-08-05T00:00:00",
        },
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["asset_id"] == "asset-1"
    assert body["count"] == 2


def test_volume_only_counts_the_requested_asset(client, mock_ingestion_key, mock_asset_access):
    """A reading on a different asset, inside the same window, must not
    be counted - this proves the query filters on asset_id, not just
    date."""
    _ingest(client, "asset-1", "SAT", 70.0, "2026-08-01T00:00:00Z")
    _ingest(client, "asset-2", "SAT", 70.0, "2026-08-01T00:00:00Z")

    response = client.get(
        "/telemetry/volume",
        params={
            "asset_id": "asset-1",
            "start_date": "2026-08-01T00:00:00",
            "end_date": "2026-08-05T00:00:00",
        },
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_volume_with_no_matching_readings_returns_zero_not_an_error(
    client, mock_ingestion_key, mock_asset_access
):
    response = client.get(
        "/telemetry/volume",
        params={
            "asset_id": "asset-with-no-data",
            "start_date": "2026-08-01T00:00:00",
            "end_date": "2026-08-05T00:00:00",
        },
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_volume_rejects_inverted_date_range_with_400(client, mock_asset_access):
    response = client.get(
        "/telemetry/volume",
        params={
            "asset_id": "asset-1",
            "start_date": "2026-08-05T00:00:00",
            "end_date": "2026-08-01T00:00:00",
        },
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 400


def test_volume_requires_start_date_and_end_date(client, mock_asset_access):
    """Unlike notification-service's alert date filters, both dates are
    required here - a bare asset_id with no range has no real use case
    for this endpoint and risks accidentally counting an asset's entire
    history."""
    response = client.get(
        "/telemetry/volume",
        params={"asset_id": "asset-1"},
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 422

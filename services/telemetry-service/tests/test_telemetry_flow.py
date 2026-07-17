"""Tests for telemetry-service's core ingestion flow."""


def test_ingest_reading_stored_unmapped(client, mock_ingestion_key):
    """A reading with no matching MetricMapping is still stored, with
    metric_definition_id left null."""
    response = client.post(
        "/telemetry",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "asset_id": "test-asset-id",
            "external_key": "SAT",
            "value": 72.5,
            "recorded_at": "2026-07-17T11:20:00Z",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["metric_definition_id"] is None
    assert body["value"] == 72.5
    assert body["source_type"] == "edge_device"


def test_ingest_reading_resolves_existing_mapping(client, mock_ingestion_key, auth_headers):
    """A reading matching an existing MetricMapping resolves
    metric_definition_id immediately at ingestion time."""
    mapping_resp = client.post(
        "/metric-mappings",
        headers=auth_headers,
        json={
            "asset_id": "test-asset-id",
            "external_key": "SAT",
            "metric_definition_id": "metric-def-123",
        },
    )
    assert mapping_resp.status_code == 201

    reading_resp = client.post(
        "/telemetry",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "asset_id": "test-asset-id",
            "external_key": "SAT",
            "value": 68.0,
            "recorded_at": "2026-07-17T11:25:00Z",
        },
    )
    assert reading_resp.status_code == 201
    assert reading_resp.json()["metric_definition_id"] == "metric-def-123"


def test_metric_mapping_backfills_prior_unmapped_readings(client, mock_ingestion_key, auth_headers):
    """Creating a mapping after readings already exist backfills those
    prior unmapped readings — the whole point of the mapping design."""
    for _ in range(3):
        resp = client.post(
            "/telemetry",
            headers={"X-Ingestion-Key": "unused-mocked-key"},
            json={
                "asset_id": "test-asset-id",
                "external_key": "SAT",
                "value": 70.0,
                "recorded_at": "2026-07-17T11:20:00Z",
            },
        )
        assert resp.status_code == 201

    mapping_resp = client.post(
        "/metric-mappings",
        headers=auth_headers,
        json={
            "asset_id": "test-asset-id",
            "external_key": "SAT",
            "metric_definition_id": "metric-def-123",
        },
    )
    assert mapping_resp.status_code == 201
    assert mapping_resp.json()["backfilled_count"] == 3


def test_ingest_rejects_missing_ingestion_key(client):
    """No X-Ingestion-Key header at all is rejected before hitting any
    business logic."""
    response = client.post(
        "/telemetry",
        json={
            "asset_id": "test-asset-id",
            "external_key": "SAT",
            "value": 72.5,
            "recorded_at": "2026-07-17T11:20:00Z",
        },
    )
    assert response.status_code == 422  # missing required header

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


def test_ingest_reading_idempotent_key_prevents_duplicate(client, mock_ingestion_key):
    """Retrying a push with the same idempotency_key returns the original
    reading instead of writing a second row."""
    payload = {
        "asset_id": "test-asset-id",
        "external_key": "SAT",
        "value": 72.5,
        "recorded_at": "2026-07-17T11:20:00Z",
        "idempotency_key": "device-abc-seq-001",
    }

    first = client.post(
        "/telemetry", headers={"X-Ingestion-Key": "unused-mocked-key"}, json=payload
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    retry = client.post(
        "/telemetry", headers={"X-Ingestion-Key": "unused-mocked-key"}, json=payload
    )
    assert retry.status_code == 200
    assert retry.json()["id"] == first_id


def test_ingest_bulk_skips_duplicate_idempotency_keys(client, mock_ingestion_key):
    """A bulk push where one item's idempotency_key was already ingested,
    and another is repeated within the same batch, only writes the
    genuinely new readings."""
    client.post(
        "/telemetry",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "asset_id": "test-asset-id",
            "external_key": "SAT",
            "value": 70.0,
            "recorded_at": "2026-07-17T11:20:00Z",
            "idempotency_key": "batch-key-1",
        },
    )

    bulk_resp = client.post(
        "/telemetry/bulk",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "readings": [
                {
                    "asset_id": "test-asset-id",
                    "external_key": "SAT",
                    "value": 71.0,
                    "recorded_at": "2026-07-17T11:21:00Z",
                    "idempotency_key": "batch-key-1",
                },
                {
                    "asset_id": "test-asset-id",
                    "external_key": "SAT",
                    "value": 72.0,
                    "recorded_at": "2026-07-17T11:22:00Z",
                    "idempotency_key": "batch-key-2",
                },
                {
                    "asset_id": "test-asset-id",
                    "external_key": "SAT",
                    "value": 73.0,
                    "recorded_at": "2026-07-17T11:23:00Z",
                    "idempotency_key": "batch-key-2",
                },
            ]
        },
    )
    assert bulk_resp.status_code == 201
    body = bulk_resp.json()
    assert body["accepted_count"] == 1
    assert body["duplicate_count"] == 2


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

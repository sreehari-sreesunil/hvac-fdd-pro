"""Tests for max_length input validation on telemetry-service's
schemas - part of this project's input validation audit (previously
zero max_length constraints existed anywhere in this codebase).
"""


def test_register_edge_device_rejects_a_name_over_255_characters(
    client, auth_headers, mock_facility_role_allowed
):
    response = client.post(
        "/edge-devices",
        json={"facility_id": "some-facility-id", "name": "a" * 256},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_metric_mapping_rejects_an_external_key_over_255_characters(client, auth_headers):
    response = client.post(
        "/metric-mappings",
        headers=auth_headers,
        json={
            "asset_id": "asset-1",
            "external_key": "a" * 256,
            "metric_definition_id": "metric-def-1",
        },
    )
    assert response.status_code == 422


def test_ingest_reading_rejects_an_external_key_over_255_characters(client, mock_ingestion_key):
    response = client.post(
        "/telemetry",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "asset_id": "asset-1",
            "external_key": "a" * 256,
            "value": 72.5,
            "recorded_at": "2026-07-17T11:20:00Z",
        },
    )
    assert response.status_code == 422


def test_ingest_reading_still_works_normally_under_the_limit(client, mock_ingestion_key):
    """Positive control - proves the limit above isn't accidentally
    rejecting normal, well-formed input."""
    response = client.post(
        "/telemetry",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "asset_id": "asset-1",
            "external_key": "SAT",
            "value": 72.5,
            "recorded_at": "2026-07-17T11:20:00Z",
        },
    )
    assert response.status_code == 201

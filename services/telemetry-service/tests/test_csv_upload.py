"""Tests for the CSV upload ingestion endpoint."""

import io


def _csv_file(content: str) -> dict:
    return {"file": ("readings.csv", io.BytesIO(content.encode("utf-8")), "text/csv")}


def test_csv_upload_ingests_valid_rows(client, mock_ingestion_key):
    """A well-formed CSV with two rows ingests both, with no errors."""
    csv_content = (
        "asset_id,external_key,value,recorded_at\n"
        "test-asset-id,SAT,72.5,2026-07-17T11:20:00Z\n"
        "test-asset-id,RAT,68.0,2026-07-17T11:21:00Z\n"
    )
    response = client.post(
        "/telemetry/csv-upload",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        files=_csv_file(csv_content),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["accepted_count"] == 2
    assert body["unmapped_count"] == 2  # no MetricMapping created in this test
    assert body["duplicate_count"] == 0
    assert body["invalid_rows"] == []


def test_csv_upload_reports_missing_required_column(client, mock_ingestion_key):
    """A CSV missing a required column is rejected up front with a single
    row-0 error, rather than attempting to process any rows."""
    csv_content = "asset_id,external_key,recorded_at\ntest-asset-id,SAT,2026-07-17T11:20:00Z\n"
    response = client.post(
        "/telemetry/csv-upload",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        files=_csv_file(csv_content),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["accepted_count"] == 0
    assert len(body["invalid_rows"]) == 1
    assert body["invalid_rows"][0]["row"] == 0
    assert "value" in body["invalid_rows"][0]["error"]


def test_csv_upload_skips_invalid_row_but_ingests_the_rest(client, mock_ingestion_key):
    """One malformed row (non-numeric value) doesn't block the rest of
    the file from being ingested — it's reported, not fatal."""
    csv_content = (
        "asset_id,external_key,value,recorded_at\n"
        "test-asset-id,SAT,not-a-number,2026-07-17T11:20:00Z\n"
        "test-asset-id,SAT,70.0,2026-07-17T11:21:00Z\n"
    )
    response = client.post(
        "/telemetry/csv-upload",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        files=_csv_file(csv_content),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["accepted_count"] == 1
    assert len(body["invalid_rows"]) == 1
    assert body["invalid_rows"][0]["row"] == 2  # header=1, first data row=2


def test_csv_upload_respects_idempotency_key(client, mock_ingestion_key):
    """A CSV row whose idempotency_key was already ingested is skipped
    and counted as a duplicate, same as the JSON bulk endpoint."""
    client.post(
        "/telemetry",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        json={
            "asset_id": "test-asset-id",
            "external_key": "SAT",
            "value": 70.0,
            "recorded_at": "2026-07-17T11:20:00Z",
            "idempotency_key": "csv-dedup-001",
        },
    )

    csv_content = (
        "asset_id,external_key,value,recorded_at,idempotency_key\n"
        "test-asset-id,SAT,71.0,2026-07-17T11:22:00Z,csv-dedup-001\n"
        "test-asset-id,SAT,72.0,2026-07-17T11:23:00Z,csv-dedup-002\n"
    )
    response = client.post(
        "/telemetry/csv-upload",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        files=_csv_file(csv_content),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["accepted_count"] == 1
    assert body["duplicate_count"] == 1


def test_csv_upload_rejects_missing_ingestion_key(client):
    """No X-Ingestion-Key header is rejected before any parsing happens."""
    csv_content = (
        "asset_id,external_key,value,recorded_at\ntest-asset-id,SAT,72.5,2026-07-17T11:20:00Z\n"
    )
    response = client.post("/telemetry/csv-upload", files=_csv_file(csv_content))
    assert response.status_code == 422

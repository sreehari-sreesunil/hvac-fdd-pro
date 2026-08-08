"""Tests for CSV upload's file size limit - a real gap found during
this project's input validation audit (there was previously no size
check of any kind before an uploaded CSV was parsed row by row).

Uses a monkeypatched, small MAX_CSV_UPLOAD_BYTES rather than a real
~50MB file - proving the size-check logic itself works correctly
doesn't require actually generating and uploading a huge file.
"""

import io


def _csv_file(content: str) -> dict:
    return {"file": ("readings.csv", io.BytesIO(content.encode("utf-8")), "text/csv")}


def test_csv_upload_rejects_a_file_over_the_size_limit(client, mock_ingestion_key, monkeypatch):
    monkeypatch.setattr("app.routers.telemetry.MAX_CSV_UPLOAD_BYTES", 100)

    csv_content = "asset_id,external_key,value,recorded_at\n" + (
        "test-asset-id,SAT,72.5,2026-07-17T11:20:00Z\n" * 10
    )
    assert len(csv_content.encode("utf-8")) > 100, "test fixture must actually exceed the limit"

    response = client.post(
        "/telemetry/csv-upload",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        files=_csv_file(csv_content),
    )
    assert response.status_code == 413


def test_csv_upload_accepts_a_file_under_the_size_limit(client, mock_ingestion_key, monkeypatch):
    """Proves the check doesn't over-trigger - a file genuinely under
    the (monkeypatched, small) limit must still be processed normally."""
    monkeypatch.setattr("app.routers.telemetry.MAX_CSV_UPLOAD_BYTES", 1_000_000)

    csv_content = (
        "asset_id,external_key,value,recorded_at\n" "test-asset-id,SAT,72.5,2026-07-17T11:20:00Z\n"
    )
    response = client.post(
        "/telemetry/csv-upload",
        headers={"X-Ingestion-Key": "unused-mocked-key"},
        files=_csv_file(csv_content),
    )
    assert response.status_code == 201
    assert response.json()["accepted_count"] == 1

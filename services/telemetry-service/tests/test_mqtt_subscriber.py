"""Tests for the MQTT subscriber's message-handling logic.

These call _authenticate_device and _handle_message directly as plain
Python functions, with a small fake "message" object standing in for a
real paho MQTTMessage. No real MQTT broker is involved or needed - see
the design discussion for why that's the right boundary for these tests.
"""

import json
from datetime import UTC

from app.core.deps import hash_key
from app.db.session import SessionLocal
from app.models.telemetry import EdgeDevice, IngestionKey, TelemetryReading
from app.mqtt.subscriber import _authenticate_device, _handle_message


class _FakeMessage:
    """Stands in for paho's mqtt.MQTTMessage. _handle_message only ever
    reads .topic and .payload off the message it's given, so this is all
    that's needed to exercise the real code path."""

    def __init__(self, topic: str, payload: bytes):
        self.topic = topic
        self.payload = payload


def _make_device_and_key(db, *, deactivated=False, revoked=False):
    """Creates a real EdgeDevice + IngestionKey row and returns
    (device_id, raw_key) - the raw key is what a real device would send,
    exactly like issue_ingestion_key hands back over HTTP."""
    device = EdgeDevice(facility_id="test-facility-id", name="Test MQTT Device")
    if deactivated:
        from datetime import datetime

        device.deactivated_at = datetime.now(UTC)
    db.add(device)
    db.flush()

    raw_key = "test-raw-mqtt-key-12345"
    ingestion_key = IngestionKey(
        edge_device_id=device.id,
        key_hash=hash_key(raw_key),
        key_prefix=raw_key[:8],
    )
    if revoked:
        from datetime import datetime

        ingestion_key.revoked_at = datetime.now(UTC)
    db.add(ingestion_key)
    db.commit()

    return device.id, raw_key


def test_authenticate_device_accepts_valid_key(client):
    db = SessionLocal()
    try:
        device_id, raw_key = _make_device_and_key(db)
        result = _authenticate_device(db, device_id, raw_key)
        assert result is not None
        assert result.id == device_id
    finally:
        db.close()


def test_authenticate_device_rejects_key_for_different_device(client):
    """A valid key for device A must not authenticate a message claiming
    to be from device B - this is the check that stops a leaked key for
    one device being used to inject data under another device's identity."""
    db = SessionLocal()
    try:
        _device_id, raw_key = _make_device_and_key(db)
        other_device = EdgeDevice(facility_id="test-facility-id", name="Other Device")
        db.add(other_device)
        db.commit()

        result = _authenticate_device(db, other_device.id, raw_key)
        assert result is None
    finally:
        db.close()


def test_authenticate_device_rejects_revoked_key(client):
    db = SessionLocal()
    try:
        device_id, raw_key = _make_device_and_key(db, revoked=True)
        result = _authenticate_device(db, device_id, raw_key)
        assert result is None
    finally:
        db.close()


def test_authenticate_device_rejects_deactivated_device(client):
    db = SessionLocal()
    try:
        device_id, raw_key = _make_device_and_key(db, deactivated=True)
        result = _authenticate_device(db, device_id, raw_key)
        assert result is None
    finally:
        db.close()


def test_handle_message_ingests_valid_reading(client):
    db = SessionLocal()
    try:
        device_id, raw_key = _make_device_and_key(db)
    finally:
        db.close()

    message = _FakeMessage(
        topic=f"telemetry/{device_id}/readings",
        payload=json.dumps(
            {
                "ingestion_key": raw_key,
                "readings": [
                    {
                        "asset_id": "test-asset-1",
                        "external_key": "SAT",
                        "value": 70.5,
                        "recorded_at": "2026-07-18T10:00:00Z",
                        "idempotency_key": "mqtt-test-001",
                    }
                ],
            }
        ).encode("utf-8"),
    )
    _handle_message(None, None, message)

    db = SessionLocal()
    try:
        reading = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.idempotency_key == "mqtt-test-001")
            .first()
        )
        assert reading is not None
        assert reading.value == 70.5
    finally:
        db.close()


def test_handle_message_rejects_invalid_ingestion_key(client):
    device_id, _raw_key = "some-device-id", "unused"
    db = SessionLocal()
    try:
        device_id, _ = _make_device_and_key(db)
    finally:
        db.close()

    message = _FakeMessage(
        topic=f"telemetry/{device_id}/readings",
        payload=json.dumps(
            {
                "ingestion_key": "totally-wrong-key",
                "readings": [
                    {
                        "asset_id": "test-asset-1",
                        "external_key": "SAT",
                        "value": 70.5,
                        "recorded_at": "2026-07-18T10:00:00Z",
                        "idempotency_key": "mqtt-should-not-exist",
                    }
                ],
            }
        ).encode("utf-8"),
    )
    _handle_message(None, None, message)  # must not raise

    db = SessionLocal()
    try:
        reading = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.idempotency_key == "mqtt-should-not-exist")
            .first()
        )
        assert reading is None
    finally:
        db.close()


def test_handle_message_ignores_malformed_topic(client):
    message = _FakeMessage(topic="not/the/right/shape/at/all", payload=b"{}")
    _handle_message(None, None, message)  # must not raise, nothing to assert on


def test_handle_message_ignores_non_json_payload(client):
    device_id = "some-device-id"
    message = _FakeMessage(topic=f"telemetry/{device_id}/readings", payload=b"not valid json{{{")
    _handle_message(None, None, message)  # must not raise


def test_handle_message_skips_invalid_reading_but_ingests_the_rest(client):
    db = SessionLocal()
    try:
        device_id, raw_key = _make_device_and_key(db)
    finally:
        db.close()

    message = _FakeMessage(
        topic=f"telemetry/{device_id}/readings",
        payload=json.dumps(
            {
                "ingestion_key": raw_key,
                "readings": [
                    {"asset_id": "test-asset-1", "external_key": "SAT"},  # missing required fields
                    {
                        "asset_id": "test-asset-1",
                        "external_key": "RAT",
                        "value": 65.0,
                        "recorded_at": "2026-07-18T10:05:00Z",
                        "idempotency_key": "mqtt-partial-batch",
                    },
                ],
            }
        ).encode("utf-8"),
    )
    _handle_message(None, None, message)

    db = SessionLocal()
    try:
        reading = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.idempotency_key == "mqtt-partial-batch")
            .first()
        )
        assert reading is not None
    finally:
        db.close()

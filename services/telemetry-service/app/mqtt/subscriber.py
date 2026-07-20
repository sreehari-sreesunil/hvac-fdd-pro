"""MQTT subscriber for telemetry-service.

Runs as a background thread inside the same FastAPI process (started at
startup in app/main.py), separate from the HTTP request path entirely.

Reuses _ingest_items() - the exact same ingestion logic already shared by
the JSON bulk and CSV upload endpoints - so there is one single place
that decides what counts as "ingesting a reading," regardless of which
door (HTTP JSON, HTTP CSV, or MQTT) it came through.

Topic scheme:   telemetry/{device_id}/readings
Payload shape:  {
    "ingestion_key": "<raw key>",
    "readings": [
        {"asset_id": "...", "external_key": "...", "value": 1.0,
         "recorded_at": "...", "idempotency_key": "..." (optional)},
        ...
    ]
}

Authentication happens at the APPLICATION layer here, not via MQTT's own
username/password mechanism - see mosquitto/mosquitto.conf for the
rationale. Each message's ingestion_key is checked against the same
IngestionKey table HTTP ingestion already uses.
"""

import json
import logging

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from app.config import settings
from app.core.deps import hash_key
from app.db.session import SessionLocal
from app.models.telemetry import EdgeDevice, IngestionKey
from app.schemas.telemetry import TelemetryReadingCreate

logger = logging.getLogger("telemetry-service.mqtt")

TOPIC_FILTER = "telemetry/+/readings"


def _authenticate_device(db, device_id: str, raw_key: str) -> EdgeDevice | None:
    """Validate an ingestion key exactly like HTTP's verify_ingestion_key
    does: hash the raw key, find a non-revoked IngestionKey row for it,
    and confirm it actually belongs to the device claimed in the topic
    (not just any valid key for any device) and that device isn't
    deactivated. Returns None on any failure - the caller logs and drops
    the message rather than raising, since there's no HTTP response
    channel to report an error back over MQTT."""
    key_hash = hash_key(raw_key)
    ingestion_key = (
        db.query(IngestionKey)
        .filter(IngestionKey.key_hash == key_hash, IngestionKey.revoked_at.is_(None))
        .first()
    )
    if ingestion_key is None:
        return None
    if ingestion_key.edge_device_id != device_id:
        return None

    device = db.query(EdgeDevice).filter(EdgeDevice.id == device_id).first()
    if device is None or device.deactivated_at is not None:
        return None

    return device


def _handle_message(client: mqtt.Client, userdata: None, message: mqtt.MQTTMessage) -> None:
    """Callback invoked by paho-mqtt, on its own background thread, for
    every message matching TOPIC_FILTER. Deliberately never raises -
    anything malformed or unauthenticated is logged and dropped."""
    from app.routers.telemetry import _ingest_items  # local import: avoids a circular import

    topic_parts = message.topic.split("/")
    if len(topic_parts) != 3 or topic_parts[0] != "telemetry" or topic_parts[2] != "readings":
        logger.warning("Ignoring MQTT message on unexpected topic: %s", message.topic)
        return
    device_id = topic_parts[1]

    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Ignoring non-JSON MQTT message on topic %s", message.topic)
        return

    raw_key = payload.get("ingestion_key")
    raw_readings = payload.get("readings")
    if not raw_key or not isinstance(raw_readings, list):
        logger.warning("Ignoring malformed MQTT payload on topic %s", message.topic)
        return

    db = SessionLocal()
    try:
        device = _authenticate_device(db, device_id, raw_key)
        if device is None:
            logger.warning("Rejected MQTT message: invalid ingestion key for device %s", device_id)
            return

        items: list[TelemetryReadingCreate] = []
        for raw_item in raw_readings:
            try:
                items.append(TelemetryReadingCreate(**raw_item))
            except ValidationError as exc:
                logger.warning("Skipping invalid reading in MQTT payload: %s", exc)

        if items:
            accepted, unmapped, duplicate = _ingest_items(db, items)
            logger.info(
                "MQTT ingest from device %s: accepted=%d unmapped=%d duplicate=%d",
                device_id,
                accepted,
                unmapped,
                duplicate,
            )
    finally:
        db.close()


def _on_connect(
    client: mqtt.Client, userdata: None, flags: dict, reason_code: int, properties: object = None
) -> None:
    if reason_code == 0:
        logger.info("Connected to MQTT broker, subscribing to %s", TOPIC_FILTER)
        client.subscribe(TOPIC_FILTER, qos=1)
    else:
        logger.error("Failed to connect to MQTT broker: reason_code=%s", reason_code)


_client: mqtt.Client | None = None


def start_mqtt_subscriber() -> None:
    """Connect to the broker and start paho's network loop on a
    background thread. Called once from app/main.py's startup event."""
    global _client
    _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    _client.on_connect = _on_connect
    _client.on_message = _handle_message
    _client.connect_async(settings.mqtt_broker_host, settings.mqtt_broker_port)
    _client.loop_start()


def stop_mqtt_subscriber() -> None:
    """Cleanly stop the background thread and disconnect. Called from
    app/main.py's shutdown event."""
    if _client is not None:
        _client.loop_stop()
        _client.disconnect()

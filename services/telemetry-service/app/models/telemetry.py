"""SQLAlchemy models for telemetry-service.

Defines EdgeDevice, IngestionKey, MetricMapping, and TelemetryReading.
All IDs are UUID strings (String(36)) to match auth-service and
asset-service's convention. No real FK to asset-service's tables exists
(cross-database, per ADR-0001) — asset_id, facility_id, and
metric_definition_id are all logical FKs only, resolved via HTTP calls
where access control matters.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class EdgeDevice(Base):
    __tablename__ = "edge_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    facility_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    ingestion_keys: Mapped[list["IngestionKey"]] = relationship(back_populates="edge_device")


class IngestionKey(Base):
    __tablename__ = "ingestion_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    edge_device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("edge_devices.id"), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    edge_device: Mapped["EdgeDevice"] = relationship(back_populates="ingestion_keys")


class MetricMapping(Base):
    __tablename__ = "metric_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    metric_definition_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    metric_definition_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    # Optional, client-supplied dedup token (per-reading, not per-batch).
    # Nullable + unique: readings that don't send one are unaffected (both
    # Postgres and SQLite treat multiple NULLs as distinct under a unique
    # index), but a repeated key on a retried push is rejected as a
    # duplicate before a second row is ever written.
    idempotency_key: Mapped[str | None] = mapped_column(
        String, nullable=True, unique=True, index=True
    )

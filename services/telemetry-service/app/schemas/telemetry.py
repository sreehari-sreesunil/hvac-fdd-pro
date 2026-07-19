"""Pydantic schemas for telemetry-service request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ---- EdgeDevice ----


class EdgeDeviceCreate(BaseModel):
    facility_id: str
    name: str


class EdgeDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    facility_id: str
    name: str
    last_seen_at: datetime | None
    deactivated_at: datetime | None
    created_at: datetime


# ---- IngestionKey ----


class IngestionKeyCreate(BaseModel):
    edge_device_id: str


class IngestionKeyCreateOut(BaseModel):
    """Returned ONLY at creation time — the one moment the raw key exists."""

    id: str
    edge_device_id: str
    api_key: str
    key_prefix: str
    created_at: datetime


class IngestionKeyOut(BaseModel):
    """Safe for listing existing keys — never includes the raw value."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    edge_device_id: str
    key_prefix: str
    created_at: datetime
    revoked_at: datetime | None


# ---- MetricMapping ----


class MetricMappingCreate(BaseModel):
    asset_id: str
    external_key: str
    metric_definition_id: str


class MetricMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    external_key: str
    metric_definition_id: str
    created_at: datetime


class MetricMappingCreateResponse(BaseModel):
    mapping: MetricMappingOut
    backfilled_count: int


# ---- TelemetryReading ----


class TelemetryReadingCreate(BaseModel):
    asset_id: str
    external_key: str
    value: float
    recorded_at: datetime
    idempotency_key: str | None = None


class TelemetryReadingBulkCreate(BaseModel):
    readings: list[TelemetryReadingCreate]


class TelemetryReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    external_key: str
    metric_definition_id: str | None
    value: float
    recorded_at: datetime
    ingested_at: datetime
    source_type: str
    idempotency_key: str | None


class TelemetryReadingBulkCreateResponse(BaseModel):
    accepted_count: int
    unmapped_count: int
    duplicate_count: int


class CsvRowError(BaseModel):
    row: int
    error: str


class TelemetryCsvUploadResponse(BaseModel):
    accepted_count: int
    unmapped_count: int
    duplicate_count: int
    invalid_rows: list[CsvRowError]

"""Telemetry ingestion, device/key management, and metric mapping endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.deps import (
    check_facility_role,
    get_current_user_id,
    hash_key,
    security,
    verify_asset_access,
    verify_ingestion_key,
)
from app.db.session import get_db
from app.models.telemetry import EdgeDevice, IngestionKey, MetricMapping, TelemetryReading
from app.schemas.telemetry import (
    EdgeDeviceCreate,
    EdgeDeviceOut,
    IngestionKeyCreateOut,
    MetricMappingCreate,
    MetricMappingCreateResponse,
    MetricMappingOut,
    TelemetryReadingBulkCreate,
    TelemetryReadingBulkCreateResponse,
    TelemetryReadingCreate,
    TelemetryReadingOut,
)
from common.roles import Role

router = APIRouter()


# ---- Edge device management (human JWT + facility role required) ----


@router.post("/edge-devices", response_model=EdgeDeviceOut, status_code=status.HTTP_201_CREATED)
async def register_edge_device(
    payload: EdgeDeviceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> EdgeDevice:
    """Register a new edge device for a facility. Requires admin or
    operator role in the facility's organization."""
    await check_facility_role(payload.facility_id, credentials, Role.admin, Role.operator)

    device = EdgeDevice(facility_id=payload.facility_id, name=payload.name)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.post(
    "/edge-devices/{device_id}/keys",
    response_model=IngestionKeyCreateOut,
    status_code=status.HTTP_201_CREATED,
)
async def issue_ingestion_key(
    device_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> IngestionKeyCreateOut:
    """Issue a new ingestion key for a device. The raw key is returned
    exactly once here — it cannot be retrieved again after this response."""
    device = db.query(EdgeDevice).filter(EdgeDevice.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge device not found")
    if device.deactivated_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device is deactivated")

    await check_facility_role(device.facility_id, credentials, Role.admin, Role.operator)

    raw_key = secrets.token_urlsafe(32)
    key_hash = hash_key(raw_key)
    key_prefix = raw_key[:8]

    ingestion_key = IngestionKey(edge_device_id=device.id, key_hash=key_hash, key_prefix=key_prefix)
    db.add(ingestion_key)
    db.commit()
    db.refresh(ingestion_key)

    return IngestionKeyCreateOut(
        id=ingestion_key.id,
        edge_device_id=ingestion_key.edge_device_id,
        api_key=raw_key,
        key_prefix=key_prefix,
        created_at=ingestion_key.created_at,
    )


# ---- Telemetry ingestion (ingestion key required, no human JWT) ----


def _resolve_metric(db: Session, asset_id: str, external_key: str) -> str | None:
    mapping = (
        db.query(MetricMapping)
        .filter(MetricMapping.asset_id == asset_id, MetricMapping.external_key == external_key)
        .first()
    )
    return mapping.metric_definition_id if mapping else None


@router.post("/telemetry", response_model=TelemetryReadingOut, status_code=status.HTTP_201_CREATED)
async def ingest_reading(
    payload: TelemetryReadingCreate,
    device: EdgeDevice = Depends(verify_ingestion_key),
    db: Session = Depends(get_db),
) -> TelemetryReading:
    """Ingest a single telemetry reading. Always stored, even if the
    metric can't yet be resolved to a known MetricDefinition."""
    metric_definition_id = _resolve_metric(db, payload.asset_id, payload.external_key)

    reading = TelemetryReading(
        asset_id=payload.asset_id,
        external_key=payload.external_key,
        metric_definition_id=metric_definition_id,
        value=payload.value,
        recorded_at=payload.recorded_at,
        source_type="edge_device",
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.post(
    "/telemetry/bulk",
    response_model=TelemetryReadingBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_readings_bulk(
    payload: TelemetryReadingBulkCreate,
    device: EdgeDevice = Depends(verify_ingestion_key),
    db: Session = Depends(get_db),
) -> TelemetryReadingBulkCreateResponse:
    """Ingest a batch of readings (e.g. from a CSV upload)."""
    unmapped_count = 0

    for item in payload.readings:
        metric_definition_id = _resolve_metric(db, item.asset_id, item.external_key)
        if metric_definition_id is None:
            unmapped_count += 1

        db.add(
            TelemetryReading(
                asset_id=item.asset_id,
                external_key=item.external_key,
                metric_definition_id=metric_definition_id,
                value=item.value,
                recorded_at=item.recorded_at,
                source_type="edge_device",
            )
        )

    db.commit()

    return TelemetryReadingBulkCreateResponse(
        accepted_count=len(payload.readings),
        unmapped_count=unmapped_count,
    )


# ---- Querying telemetry (human JWT + asset access required) ----


@router.get("/telemetry", response_model=list[TelemetryReadingOut])
async def list_readings(
    asset_id: str,
    metric_definition_id: str | None = None,
    db: Session = Depends(get_db),
    _user_id: str = Depends(verify_asset_access),
) -> list[TelemetryReading]:
    """List readings for an asset, optionally filtered by metric."""
    query = db.query(TelemetryReading).filter(TelemetryReading.asset_id == asset_id)
    if metric_definition_id is not None:
        query = query.filter(TelemetryReading.metric_definition_id == metric_definition_id)
    return query.order_by(TelemetryReading.recorded_at.desc()).limit(500).all()


@router.get("/telemetry/unmapped", response_model=list[str])
async def list_unmapped_keys(
    asset_id: str,
    db: Session = Depends(get_db),
    _user_id: str = Depends(verify_asset_access),
) -> list[str]:
    """List distinct external_keys for an asset that have no resolved
    metric_definition_id yet — surfaces what needs mapping."""
    rows = (
        db.query(TelemetryReading.external_key)
        .filter(
            TelemetryReading.asset_id == asset_id,
            TelemetryReading.metric_definition_id.is_(None),
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


# ---- Metric mapping (human JWT) ----


@router.post(
    "/metric-mappings",
    response_model=MetricMappingCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_metric_mapping(
    payload: MetricMappingCreate,
    db: Session = Depends(get_db),
    _user_id: str = Depends(get_current_user_id),
) -> MetricMappingCreateResponse:
    """Create a metric mapping and backfill any prior unmapped readings
    that match (asset_id, external_key)."""
    mapping = MetricMapping(
        asset_id=payload.asset_id,
        external_key=payload.external_key,
        metric_definition_id=payload.metric_definition_id,
    )
    db.add(mapping)
    db.flush()

    backfilled_count = (
        db.query(TelemetryReading)
        .filter(
            TelemetryReading.asset_id == payload.asset_id,
            TelemetryReading.external_key == payload.external_key,
            TelemetryReading.metric_definition_id.is_(None),
        )
        .update({"metric_definition_id": payload.metric_definition_id})
    )

    db.commit()
    db.refresh(mapping)

    return MetricMappingCreateResponse(
        mapping=MetricMappingOut.model_validate(mapping),
        backfilled_count=backfilled_count,
    )

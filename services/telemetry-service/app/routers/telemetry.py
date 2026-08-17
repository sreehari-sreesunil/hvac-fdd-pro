"""Telemetry ingestion, device/key management, and metric mapping endpoints."""

import csv
import hashlib
import io
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
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
    CsvRowError,
    EdgeDeviceCreate,
    EdgeDeviceOut,
    IngestionKeyCreateOut,
    MetricMappingCreate,
    MetricMappingCreateResponse,
    MetricMappingOut,
    TelemetryCsvUploadResponse,
    TelemetryReadingBulkCreate,
    TelemetryReadingBulkCreateResponse,
    TelemetryReadingCreate,
    TelemetryReadingOut,
    TelemetryVolumeOut,
)
from common.roles import Role

router = APIRouter()

# Real, but partial, mitigation - see ingest_readings_csv below. Not a
# complete DoS defense on its own: a genuinely complete guarantee also
# needs a reverse-proxy/load-balancer-level request body size limit,
# which doesn't exist yet in this project's current architecture (no
# reverse proxy in front of these services at all today) - that's a
# real, honest gap, not silently claimed to be solved here. 50MB is
# generous headroom for a real bulk upload (the largest real ingestion
# this project has done - ~18,000 readings via ingest_test_data.py -
# produced a telemetry_db backup of 5.4MB, and that's compressed
# database storage, not even raw CSV text) while still bounding the
# worst case.
MAX_CSV_UPLOAD_BYTES = 50 * 1024 * 1024

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


@router.get("/edge-devices", response_model=list[EdgeDeviceOut])
async def list_edge_devices(
    facility_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> list[EdgeDevice]:
    """List every edge device registered for a facility.

    Real gap found live: POST /edge-devices (create) existed with no
    corresponding GET (list) at all - a registered device had no way
    to ever be seen again after creation, which is why the frontend's
    device management page never showed anything. Any real facility
    role (admin, operator, or viewer) can view the list - only
    registering a new device is role-gated the same way creation
    already is.
    """
    await check_facility_role(facility_id, credentials, Role.admin, Role.operator, Role.viewer)
    return db.query(EdgeDevice).filter(EdgeDevice.facility_id == facility_id).all()


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


def _derive_content_key(item: TelemetryReadingCreate) -> str:
    """Deterministic fallback idempotency key for a reading that didn't
    supply its own. Hashes the reading's full content (not just
    asset_id/external_key/recorded_at) so a genuinely different value at
    the same timestamp - a real correction, not a duplicate - still gets
    a distinct key and is accepted, not silently dropped."""
    raw = f"{item.asset_id}|{item.external_key}|{item.value}|{item.recorded_at.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _ingest_items(db: Session, items: list[TelemetryReadingCreate]) -> tuple[int, int, int]:
    """Insert a batch of already-validated readings, resolving metrics and
    skipping idempotency-key duplicates.

    Shared by both the JSON bulk endpoint and the CSV upload endpoint so
    the two ingestion paths can never silently drift apart — there is
    exactly one place where "what counts as a duplicate" and "how a
    metric gets resolved at write time" are decided.

    Returns:
        (accepted_count, unmapped_count, duplicate_count)
    """
    requested_keys = {item.idempotency_key or _derive_content_key(item) for item in items}
    existing_keys: set[str] = set()
    if requested_keys:
        rows = (
            db.query(TelemetryReading.idempotency_key)
            .filter(TelemetryReading.idempotency_key.in_(requested_keys))
            .all()
        )
        existing_keys = {r[0] for r in rows}

    seen_in_batch: set[str] = set()
    accepted_count = 0
    unmapped_count = 0
    duplicate_count = 0

    for item in items:
        # A caller-supplied idempotency_key is honored as-is. Absent one
        # (the common case for a plain CSV upload with no
        # idempotency_key column - exactly what a real accidental
        # re-upload of the same file looks like), derive one from the
        # reading's own content instead of leaving it unprotected. This
        # means re-submitting IDENTICAL data (same asset, metric,
        # value, and timestamp) correctly dedupes, while a genuinely
        # different value at the same timestamp - a real correction or
        # a distinct reading - still gets a different hash and is
        # accepted as new data, not silently dropped. Found and fixed
        # after a real accidental duplicate CSV upload during a live
        # walkthrough produced silent, unprotected duplicate rows.
        key = item.idempotency_key or _derive_content_key(item)
        if key in existing_keys or key in seen_in_batch:
            duplicate_count += 1
            continue
        seen_in_batch.add(key)

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
                idempotency_key=key,
            )
        )
        accepted_count += 1

    db.commit()
    return accepted_count, unmapped_count, duplicate_count


_REQUIRED_CSV_COLUMNS = {"asset_id", "external_key", "value", "recorded_at"}


def _parse_csv_rows(raw: bytes) -> tuple[list[TelemetryReadingCreate], list[CsvRowError]]:
    """Parse an uploaded CSV file into validated TelemetryReadingCreate
    items, plus a list of per-row errors for anything that didn't parse.

    Row-level validation, not all-or-nothing: one bad row never prevents
    the rest of the file from being ingested. Row numbers in the returned
    errors count from 2, since row 1 is the header line, matching what a
    person would see if they opened the file in a spreadsheet."""
    text = raw.decode("utf-8-sig")  # utf-8-sig strips a BOM if Excel added one
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return [], [CsvRowError(row=0, error="CSV file has no header row")]

    normalized_fieldnames = {name.strip().lower() for name in reader.fieldnames}
    missing = _REQUIRED_CSV_COLUMNS - normalized_fieldnames
    if missing:
        return [], [
            CsvRowError(row=0, error=f"Missing required column(s): {', '.join(sorted(missing))}")
        ]

    valid_items: list[TelemetryReadingCreate] = []
    errors: list[CsvRowError] = []

    for line_number, raw_row in enumerate(reader, start=2):
        row = {
            (k.strip().lower() if k else k): (v.strip() if v is not None else v)
            for k, v in raw_row.items()
        }
        idempotency_key = row.get("idempotency_key") or None

        try:
            item = TelemetryReadingCreate(
                # csv.DictReader can produce a None value for a row
                # shorter than the header (a malformed CSV row) - same
                # reasoning as value/recorded_at's existing type:ignore
                # below: a None here safely becomes a Pydantic
                # ValidationError, caught by the except clause right
                # below and turned into a per-row CsvRowError, not a
                # live bug reaching this far.
                asset_id=row["asset_id"],  # type: ignore[arg-type]
                external_key=row["external_key"],  # type: ignore[arg-type]
                value=row["value"],  # type: ignore[arg-type]
                recorded_at=row["recorded_at"],  # type: ignore[arg-type]
                idempotency_key=idempotency_key,
            )
        except (ValidationError, KeyError) as exc:
            errors.append(CsvRowError(row=line_number, error=str(exc)))
            continue

        valid_items.append(item)

    return valid_items, errors


@router.post("/telemetry", response_model=TelemetryReadingOut, status_code=status.HTTP_201_CREATED)
async def ingest_reading(
    payload: TelemetryReadingCreate,
    response: Response,
    device: EdgeDevice = Depends(verify_ingestion_key),
    db: Session = Depends(get_db),
) -> TelemetryReading:
    """Ingest a single telemetry reading. Always stored, even if the
    metric can't yet be resolved to a known MetricDefinition.

    A reading with a matching idempotency_key (caller-supplied, or
    derived from the reading's own content if absent - same fallback
    as _ingest_items, see _derive_content_key's docstring for why) is
    returned as-is (status 200) instead of writing a duplicate row -
    this is what makes retried pushes from flaky edge networks safe.
    This endpoint previously only checked a caller-supplied key,
    leaving it unprotected against a genuine retry with no key at all
    - a real, live-caught gap: this is the endpoint's own single-
    reading path, not the CSV/bulk/MQTT paths that already got this
    fix (they all share _ingest_items; this one has its own separate
    logic due to its different response contract - the actual reading
    object, not just counts)."""
    key = payload.idempotency_key or _derive_content_key(payload)
    existing = db.query(TelemetryReading).filter(TelemetryReading.idempotency_key == key).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    metric_definition_id = _resolve_metric(db, payload.asset_id, payload.external_key)

    reading = TelemetryReading(
        asset_id=payload.asset_id,
        external_key=payload.external_key,
        metric_definition_id=metric_definition_id,
        value=payload.value,
        recorded_at=payload.recorded_at,
        source_type="edge_device",
        idempotency_key=key,
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
    """Ingest a batch of structured JSON readings.

    Idempotency is per-item (each reading may carry its own
    idempotency_key), not per-batch. Any item whose key already exists in
    the table — or is repeated earlier in the same batch — is skipped and
    counted in duplicate_count rather than written again."""
    accepted_count, unmapped_count, duplicate_count = _ingest_items(db, payload.readings)

    return TelemetryReadingBulkCreateResponse(
        accepted_count=accepted_count,
        unmapped_count=unmapped_count,
        duplicate_count=duplicate_count,
    )


@router.post(
    "/telemetry/csv-upload",
    response_model=TelemetryCsvUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_readings_csv(
    file: UploadFile = File(...),
    device: EdgeDevice = Depends(verify_ingestion_key),
    db: Session = Depends(get_db),
) -> TelemetryCsvUploadResponse:
    """Ingest a batch of readings from an uploaded CSV file.

    Expected columns: asset_id, external_key, value, recorded_at, and
    optionally idempotency_key. Column names are matched case-insensitively.

    Row-level validation, not all-or-nothing: a malformed row (bad number,
    bad date, missing value) is skipped and reported in invalid_rows with
    its row number and the reason — it does not fail the rest of the
    upload. This matches telemetry-service's core "never drop data"
    principle for anything that *can* be parsed. A structural problem
    (missing required column, empty file) is reported the same way, as a
    single row-0 entry in invalid_rows, rather than a different error
    shape.

    Rejects files over MAX_CSV_UPLOAD_BYTES before the expensive
    row-by-row parsing/DB-insertion work runs - a real, but partial,
    mitigation for an unbounded-upload resource-exhaustion risk found
    during this project's input validation audit (there was previously
    no size check of any kind here). See MAX_CSV_UPLOAD_BYTES's own
    comment for what this does and doesn't guarantee.
    """
    raw = await file.read()
    if len(raw) > MAX_CSV_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"CSV file too large - max {MAX_CSV_UPLOAD_BYTES // (1024 * 1024)}MB",
        )
    items, invalid_rows = _parse_csv_rows(raw)

    if items:
        accepted_count, unmapped_count, duplicate_count = _ingest_items(db, items)
    else:
        accepted_count, unmapped_count, duplicate_count = 0, 0, 0

    return TelemetryCsvUploadResponse(
        accepted_count=accepted_count,
        unmapped_count=unmapped_count,
        duplicate_count=duplicate_count,
        invalid_rows=invalid_rows,
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


@router.get("/telemetry/volume", response_model=TelemetryVolumeOut)
async def get_telemetry_volume(
    asset_id: str,
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    _user_id: str = Depends(verify_asset_access),
) -> TelemetryVolumeOut:
    """Count how many readings were ingested for an asset in a date
    range - a rough "is data actually flowing" signal.

    Both start_date and end_date are required (unlike notification-
    service's alert date filters, which are both optional) - this
    endpoint only exists to answer "how much data in THIS period", so
    an unbounded query has no real use case here and would just risk
    someone accidentally counting an asset's entire history.

    Built for notification-service's facility report, which calls this
    once per asset in a facility to build the per-asset ingestion_count
    field alongside alert_count (see services/notification-service/app/
    schemas/report.py's ReportAssetSummary, currently missing this field
    pending exactly this endpoint).
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    count = (
        db.query(TelemetryReading)
        .filter(TelemetryReading.asset_id == asset_id)
        .filter(TelemetryReading.recorded_at >= start_date)
        .filter(TelemetryReading.recorded_at < end_date)
        .count()
    )
    return TelemetryVolumeOut(asset_id=asset_id, count=count)


# ---- Metric mapping (human JWT) ----


@router.get("/metric-mappings", response_model=list[MetricMappingOut])
async def list_metric_mappings(
    asset_id: str,
    db: Session = Depends(get_db),
    _user_id: str = Depends(verify_asset_access),
) -> list[MetricMapping]:
    """List every existing metric mapping for an asset.

    The complement of GET /telemetry/unmapped (which lists raw keys
    with NO mapping yet) - this lists what's already mapped. Neither
    endpoint existed as a pair until now; only the unmapped-keys side
    was built originally. This is needed for the sensor-mapping/
    model-readiness feature: showing a user their asset's CURRENT
    mapping state (not just what's missing) is required to build a
    real "here's what you have vs. what a model needs" comparison.

    Uses verify_asset_access (not just get_current_user_id, which
    create_metric_mapping below uses) - matching the stricter pattern
    already used by list_readings/list_unmapped_keys/
    get_telemetry_volume for read endpoints scoped to one asset.
    """
    return (
        db.query(MetricMapping)
        .filter(MetricMapping.asset_id == asset_id)
        .order_by(MetricMapping.created_at.desc())
        .all()
    )


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

"""Alert engine endpoints.

POST /alerts is the generic sink every detector writes into (currently:
ml-service's baseline-deviation scheduler; designed so a future
threshold-checker or classifier-based detector can call the exact same
endpoint without any change here - see app/models/alert.py's docstring).

GET/PATCH endpoints are user-facing, gated by the same asset-org
membership check every other service in this project uses.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import verify_asset_access, verify_internal_api_key
from app.db.session import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate,
    _: None = Depends(verify_internal_api_key),
    db: Session = Depends(get_db),
) -> Alert:
    """Internal endpoint - only trusted services call this directly."""
    alert = Alert(
        asset_id=payload.asset_id,
        metric_definition_id=payload.metric_definition_id,
        source=payload.source,
        severity=payload.severity,
        message=payload.message,
        details=payload.details,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/{asset_id}", response_model=list[AlertOut])
async def list_alerts(
    asset_id: str,
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    start_date: datetime | None = Query(
        None, description="Only alerts created at or after this timestamp (ISO 8601)."
    ),
    end_date: datetime | None = Query(
        None, description="Only alerts created at or before this timestamp (ISO 8601)."
    ),
    limit: int = Query(50, le=200),
    _user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """List alerts for one asset, newest first, optionally filtered.

    start_date/end_date are both optional and independent - either can be
    given alone (an open-ended range) or together (a bounded window). Added
    to support the facility-level report aggregation endpoint, which needs
    to ask "alerts in this period" rather than always the most recent N -
    see notification-service's GET /reports/{facility_id}.
    """
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    q = db.query(Alert).filter(Alert.asset_id == asset_id)
    if status_filter:
        q = q.filter(Alert.status == status_filter)
    if severity:
        q = q.filter(Alert.severity == severity)
    if start_date is not None:
        q = q.filter(Alert.created_at >= start_date)
    if end_date is not None:
        q = q.filter(Alert.created_at <= end_date)
    return q.order_by(Alert.created_at.desc()).limit(limit).all()


@router.patch("/{asset_id}/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    asset_id: str,
    alert_id: str,
    user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.asset_id == asset_id).first()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    # SQLAlchemy legacy Column() style: mypy infers the instance attribute
    # itself as Column[T] from the class-level Column() declaration, so a
    # plain-value assignment looks like a type mismatch to mypy even
    # though it's exactly how SQLAlchemy instrumented attributes are meant
    # to be set - a known, real SQLAlchemy typing limitation, not a bug.
    alert.status = "acknowledged"  # type: ignore[assignment]
    alert.acknowledged_at = datetime.utcnow()  # type: ignore[assignment]
    alert.acknowledged_by = user_id  # type: ignore[assignment]
    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/{asset_id}/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    asset_id: str,
    alert_id: str,
    user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.asset_id == asset_id).first()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    # Same SQLAlchemy Column[T]-vs-T limitation as acknowledge_alert above.
    alert.status = "resolved"  # type: ignore[assignment]
    alert.resolved_at = datetime.utcnow()  # type: ignore[assignment]
    alert.resolved_by = user_id  # type: ignore[assignment]
    db.commit()
    db.refresh(alert)
    return alert

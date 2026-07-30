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
    limit: int = Query(50, le=200),
    _user_id: str = Depends(verify_asset_access),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """List alerts for one asset, newest first, optionally filtered."""
    q = db.query(Alert).filter(Alert.asset_id == asset_id)
    if status_filter:
        q = q.filter(Alert.status == status_filter)
    if severity:
        q = q.filter(Alert.severity == severity)
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
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = user_id
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
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = user_id
    db.commit()
    db.refresh(alert)
    return alert

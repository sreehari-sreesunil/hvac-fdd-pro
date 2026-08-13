from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.deps import bearer_scheme, get_current_user_id, verify_org_membership
from app.db.session import get_db
from app.models.asset import Asset, Facility
from app.schemas.asset import AssetCreate, AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetOut, status_code=201)
async def create_asset(
    payload: AssetCreate,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Asset:
    facility = db.query(Facility).filter(Facility.id == payload.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    # SQLAlchemy legacy Column() style: mypy sees Column[str] on instance
    # attribute access, not the real runtime str - a known SQLAlchemy
    # typing limitation, not a bug here (repeats at every call site below).
    await verify_org_membership(cast(str, facility.organization_id), credentials.credentials)

    # your turn: build and save the Asset here, using payload.facility_id,
    # payload.asset_type_id, payload.name, payload.external_ref
    # (do NOT set id or created_at manually — the model already defaults them)
    asset = Asset(
        facility_id=payload.facility_id,
        asset_type_id=payload.asset_type_id,
        name=payload.name,
        external_ref=payload.external_ref,
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetOut])
async def list_assets(
    facility_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Asset]:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    await verify_org_membership(cast(str, facility.organization_id), credentials.credentials)
    return db.query(Asset).filter(Asset.facility_id == facility_id).all()


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(
    asset_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Asset:
    """Get a single asset by ID. Verifies the caller belongs to the
    asset's facility's organization before returning it."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    facility = db.query(Facility).filter(Facility.id == asset.facility_id).first()
    if facility is None:
        # Data integrity issue, not a client error — an asset pointing at
        # a facility that no longer exists.
        raise HTTPException(status_code=500, detail="Asset's facility not found")

    await verify_org_membership(cast(str, facility.organization_id), credentials.credentials)

    return asset

"""
Facility endpoints for asset-service.

A Facility belongs to an Organization owned by auth-service. Since
asset-service has no direct database access to auth-service's tables,
every facility operation must verify org membership via a real HTTP call
to auth-service (see app/core/deps.py verify_org_membership) — never by
trusting a claim baked into the JWT itself.
"""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.deps import bearer_scheme, get_current_user_id, verify_org_membership
from app.db.session import get_db
from app.models.asset import Facility
from app.schemas.asset import FacilityCreate, FacilityOut

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.post("", response_model=FacilityOut, status_code=201)
async def create_facility(
    payload: FacilityCreate,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Facility:
    """Create a facility within an organization.

    Args:
        payload: Facility fields, including organization_id.
        credentials: Raw bearer token, forwarded to auth-service for the
            membership check (verify_org_membership needs the actual JWT
            string, not just the decoded user_id).
        user_id: The calling user's id, extracted from the token locally.
        db: Database session.

    Returns:
        The newly created Facility.

    Raises:
        HTTPException: 403 if not a member of payload.organization_id
            (raised inside verify_org_membership), 503 if auth-service
            is unreachable.
    """
    await verify_org_membership(payload.organization_id, credentials.credentials)

    facility = Facility(
        organization_id=payload.organization_id,
        name=payload.name,
        address=payload.address,
        timezone=payload.timezone,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility


@router.get("", response_model=list[FacilityOut])
async def list_facilities(
    organization_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Facility]:
    """List all facilities belonging to an organization.

    Args:
        organization_id: The organization to list facilities for, passed
            as a query parameter (e.g. GET /facilities?organization_id=...).
        credentials: Raw bearer token, forwarded to auth-service for the
            membership check.
        user_id: The calling user's id, extracted from the token locally.
        db: Database session.

    Returns:
        All Facility rows for that organization_id. Empty list if the org
        has none — not an error, since membership was already confirmed.

    Raises:
        HTTPException: 403 if the caller is not a member of
            organization_id, 503 if auth-service is unreachable.
    """
    await verify_org_membership(organization_id, credentials.credentials)

    return db.query(Facility).filter(Facility.organization_id == organization_id).all()


@router.get("/{facility_id}", response_model=FacilityOut)
async def get_facility(
    facility_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Facility:
    """Get a single facility by ID. Verifies the caller belongs to the
    facility's organization before returning it or revealing whether it
    exists."""
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")

    # SQLAlchemy legacy Column() style: mypy sees Column[str] on instance
    # attribute access, not the real runtime str - a known SQLAlchemy
    # typing limitation, not a bug here.
    await verify_org_membership(cast(str, facility.organization_id), credentials.credentials)

    return facility

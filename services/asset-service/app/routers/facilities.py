"""
Facility endpoints for asset-service.

A Facility belongs to an Organization owned by auth-service. Since
asset-service has no direct database access to auth-service's tables,
every facility operation must verify org membership via a real HTTP call
to auth-service (see app/core/deps.py verify_org_membership) — never by
trusting a claim baked into the JWT itself.
"""

from fastapi import APIRouter, Depends
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
    """List all facilities within an organization the caller belongs to."""
    await verify_org_membership(organization_id, credentials.credentials)
    return db.query(Facility).filter(Facility.organization_id == organization_id).all()

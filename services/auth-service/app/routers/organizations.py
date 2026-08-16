"""Organization endpoints: creation and listing, scoped to the caller.

An Organization is the top-level tenant boundary in this platform — every
Facility, Asset, and piece of Telemetry (owned by other services) traces
back to one Organization via ownership chains enforced at the service layer.
"""

from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import Membership, Organization, Role, User
from app.schemas.auth import MemberInvite, MemberOut, OrganizationCreate, OrganizationOut

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    """Create a new organization and make the creator its admin.

    Returns:
        The newly created Organization, with role="admin" — the creator is
        always granted admin, so this is known without an extra query.
    """
    org = Organization(name=payload.name)
    db.add(org)
    db.flush()

    membership = Membership(user_id=current_user.id, organization_id=org.id, role=Role.admin)
    db.add(membership)
    db.commit()
    db.refresh(org)

    # SQLAlchemy's legacy declarative Column() style types instance
    # attribute access as Column[T] under mypy even though it's the real T
    # at runtime - a known, real SQLAlchemy typing limitation, not a bug
    # here (same pattern repeats at every ORM-instance-to-schema boundary
    # in this codebase).
    return OrganizationOut(
        id=cast(str, org.id),
        name=cast(str, org.name),
        created_at=cast(datetime, org.created_at),
        role=Role.admin,
    )


@router.get("", response_model=list[OrganizationOut])
def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrganizationOut]:
    """List every organization the current user belongs to.

    Args:
        current_user: The authenticated caller.
        db: Database session.

    Returns:
        Organizations with the caller's role in each — this is what
        other services (e.g. asset-service) rely on to enforce
        org-scoped RBAC without needing direct database access to
        auth-service's tables.
    """
    rows = (
        db.query(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .filter(Membership.user_id == current_user.id)
        .all()
    )
    return [
        OrganizationOut(id=org.id, name=org.name, created_at=org.created_at, role=role)
        for org, role in rows
    ]


@router.post("/{org_id}/invite", status_code=status.HTTP_201_CREATED)
def invite_member(
    org_id: str,
    payload: MemberInvite,
    membership: Membership = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
) -> dict:
    """Add an existing user to an organization with a given role.

    Only admins of the target organization may invite members. Note this
    is the DIRECT-ADD flow — attaching a role to a user who already has an
    account. The real "email invite link for someone with no account yet"
    flow is a Week 8 (complete user journey) feature, not built here.

    Args:
        org_id: The organization to add the member to (path parameter —
            this is what require_role(Role.admin) checks against).
        payload: The invitee's email and intended role.
        membership: Unused directly, but its presence in the signature is
            what enforces "caller must be an admin of org_id" before this
            function body even runs.
        db: Database session.

    Returns:
        A confirmation dict with the new member's user_id and role.

    Raises:
        HTTPException: 404 if no user with that email exists yet.
        HTTPException: 400 if the user is already a member of this org.
    """
    invited_user = db.query(User).filter(User.email == payload.email).first()
    if not invited_user:
        raise HTTPException(
            status_code=404,
            detail="No user with that email exists yet — email invite links are a Week 8 item",
        )

    existing = (
        db.query(Membership)
        .filter(Membership.user_id == invited_user.id, Membership.organization_id == org_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")

    new_membership = Membership(user_id=invited_user.id, organization_id=org_id, role=payload.role)
    db.add(new_membership)
    db.commit()
    return {"detail": "Member added", "user_id": invited_user.id, "role": payload.role}


@router.get("/{org_id}/members", response_model=list[MemberOut])
def list_members(
    org_id: str,
    membership: Membership = Depends(require_role(Role.admin, Role.operator, Role.viewer)),
    db: Session = Depends(get_db),
) -> list[MemberOut]:
    """List every member of an organization.

    Any real member (any of the three roles) can view who else is in
    their org - only inviting/modifying membership is admin-gated, not
    viewing it, matching typical RBAC conventions.

    Args:
        org_id: The organization to list members for (path parameter -
            this is what require_role(...) checks against).
        membership: Unused directly, but its presence enforces "caller
            must be a member of org_id, any role" before this function
            body runs.
        db: Database session.

    Returns:
        Every membership row for this org, joined with each user's email.
    """
    rows = (
        db.query(Membership, User)
        .join(User, Membership.user_id == User.id)
        .filter(Membership.organization_id == org_id)
        .all()
    )
    return [
        MemberOut(user_id=cast(str, m.user_id), email=cast(str, u.email), role=cast(Role, m.role))
        for m, u in rows
    ]

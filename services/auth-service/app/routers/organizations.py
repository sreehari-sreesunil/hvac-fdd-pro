"""Organization endpoints: creation and listing, scoped to the caller.

An Organization is the top-level tenant boundary in this platform — every
Facility, Asset, and piece of Telemetry (owned by other services) traces
back to one Organization via ownership chains enforced at the service layer.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import Membership, Organization, Role, User
from app.schemas.auth import MemberInvite, OrganizationCreate, OrganizationOut

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

    return OrganizationOut(id=org.id, name=org.name, created_at=org.created_at, role=Role.admin)


@router.get("", response_model=list[OrganizationOut])
def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Organization]:
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

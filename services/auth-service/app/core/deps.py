"""Authentication and authorization dependencies for auth-service.

These are FastAPI dependency functions, injected into router endpoints via
Depends(...). They handle two distinct concerns:
  - get_current_user: WHO is making this request (authentication)
  - require_role: WHAT they're allowed to do in a given organization (authorization/RBAC)
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.user import Membership, Role, User
from common.security import decode_and_verify_token

# Registering this scheme is what makes Swagger UI show the "Authorize"
# padlock and a proper Bearer-token input field.
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the currently authenticated user from a Bearer JWT.

    Args:
        credentials: Parsed Authorization header, injected by the HTTPBearer
            security scheme. credentials.credentials is the raw token string
            (the "Bearer " prefix is already stripped for us).
        db: Database session, injected by FastAPI.

    Returns:
        The authenticated, active User.

    Raises:
        HTTPException: 401 if the token is invalid or expired, or the user
            no longer exists / is deactivated.
    """
    token = credentials.credentials

    user_id = decode_and_verify_token(
        token, settings.jwt_secret_key, settings.jwt_algorithm, expected_type="access"
    )
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    return user


def require_role(*allowed_roles: Role) -> Callable[..., Membership]:
    """Build a FastAPI dependency that enforces org-scoped role membership.

    This is a dependency FACTORY: calling require_role(Role.admin) returns a
    configured dependency function that only allows admins, for use like:
        Depends(require_role(Role.admin, Role.operator))

    Args:
        *allowed_roles: One or more Role values permitted for the endpoint.

    Returns:
        A FastAPI dependency function that resolves to the caller's
        Membership if authorized, or raises 403 otherwise.
    """

    def checker(
        org_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Membership:
        """Check that current_user is a member of org_id with an allowed role."""
        membership = (
            db.query(Membership)
            .filter(Membership.user_id == current_user.id, Membership.organization_id == org_id)
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization"
            )
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this action"
            )
        return membership

    return checker

"""Authentication and authorization dependencies for asset-service.

Unlike auth-service, this service does not own User/Organization/Membership
data — it calls auth-service's API to verify org membership and role. This
is a real service-to-service call, the first one in this platform.
"""

from typing import cast

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from common.security import decode_and_verify_token

bearer_scheme = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Resolve the calling user's id from a Bearer JWT.

    Unlike auth-service's get_current_user, this returns just the user id
    string, not a full User object — asset-service has no User table to
    load one from.

    Raises:
        HTTPException: 401 if the token is invalid or expired.
    """
    user_id = decode_and_verify_token(
        credentials.credentials,
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        expected_type="access",
    )
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return cast(str, user_id)


async def verify_org_membership(org_id: str, token: str) -> str:
    """Call auth-service to confirm the user belongs to org_id, and return their role.

    Args:
        org_id: The organization to check membership in.
        token: The raw JWT to forward to auth-service.

    Returns:
        The caller's actual role in that org (e.g. "admin", "operator", "viewer").

    Raises:
        HTTPException: 403 if not a member, 503 if auth-service is unreachable.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(
                f"{settings.auth_service_url}/organizations",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not reach auth-service to verify organization membership",
            ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization"
        )

    orgs = response.json()
    matching_org = next((org for org in orgs if org["id"] == org_id), None)
    if matching_org is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization"
        )

    return cast(str, matching_org["role"])

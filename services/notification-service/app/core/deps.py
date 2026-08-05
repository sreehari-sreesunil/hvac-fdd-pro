"""Auth dependencies for notification-service - two separate trust models.

verify_asset_access: for user-facing endpoints (GET/PATCH /alerts),
mirrors every other service's pattern exactly - resolves asset ->
facility -> org membership via asset-service, verifies the human JWT
locally via the shared common.security module.

verify_facility_access: same pattern as verify_asset_access, one level
up - for GET /reports/{facility_id}, which aggregates across a whole
facility's assets rather than checking one asset at a time.

verify_internal_api_key: for internal, service-to-service endpoints
(POST /alerts, called by ml-service's scheduler) - a single shared
secret, matching the trust level of services already inside the
Docker network. Deliberately NOT the same mechanism as
telemetry-service's per-device IngestionKey system, which exists to
let individual EXTERNAL, untrusted devices be independently revoked -
a mismatched, heavier tool for a same-network internal call.
"""

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from common.security import decode_and_verify_token

security = HTTPBearer()


async def verify_asset_access(
    asset_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify the caller has org-level access to the asset. Returns the
    caller's user_id."""
    token = credentials.credentials

    async with httpx.AsyncClient() as client:
        try:
            asset_resp = await client.get(
                f"{settings.asset_service_url}/assets/{asset_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="asset-service unavailable",
            ) from err

    if asset_resp.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    if asset_resp.status_code == status.HTTP_403_FORBIDDEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this asset's organization",
        )
    if asset_resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unexpected response from asset-service",
        )

    user_id = decode_and_verify_token(token, settings.jwt_secret_key, settings.jwt_algorithm)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return user_id


async def verify_facility_access(
    facility_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify the caller has org-level access to the facility. Returns the
    caller's user_id.

    Same shape as verify_asset_access above, one level up the hierarchy -
    added for GET /reports/{facility_id}, which aggregates across every
    asset in a facility rather than checking one asset at a time.
    asset-service's GET /facilities/{facility_id} already does its own
    404 (not found) and 403 (not a member, via verify_org_membership)
    checks internally, so this dependency just forwards the token and
    trusts those response codes - it does not re-derive org membership
    itself.
    """
    token = credentials.credentials

    async with httpx.AsyncClient() as client:
        try:
            facility_resp = await client.get(
                f"{settings.asset_service_url}/facilities/{facility_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="asset-service unavailable",
            ) from err

    if facility_resp.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    if facility_resp.status_code == status.HTTP_403_FORBIDDEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this facility's organization",
        )
    if facility_resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unexpected response from asset-service",
        )

    user_id = decode_and_verify_token(token, settings.jwt_secret_key, settings.jwt_algorithm)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return user_id


async def verify_internal_api_key(
    x_internal_api_key: str = Header(...),
) -> None:
    """Verify a trusted internal caller (e.g. ml-service's alert
    scheduler). Constant-time comparison isn't used here deliberately -
    this key lives only in Docker-internal env vars, never sent over a
    public network, so timing-attack resistance isn't the relevant
    threat model (unlike a public-facing secret)."""
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )

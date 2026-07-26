"""Auth dependency for ml-service.

Mirrors telemetry-service's verify_asset_access exactly: resolves the
asset -> facility -> organization membership check via asset-service,
then verifies the human JWT locally via the shared common.security module.
No separate auth mechanism invented for ml-service - same pattern as every
other service in this project.
"""

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from common.security import decode_and_verify_token

security = HTTPBearer()


async def verify_asset_access(
    asset_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify the caller has org-level access to the asset, by asking
    asset-service (which itself resolves asset -> facility -> org and
    checks membership via auth-service). Returns the caller's user_id."""
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

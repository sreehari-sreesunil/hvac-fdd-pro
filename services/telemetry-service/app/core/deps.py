"""Auth dependencies for telemetry-service.

Two distinct verification paths, deliberately kept separate:

1. verify_ingestion_key — for high-volume telemetry write endpoints.
   Verifies a device API key entirely locally (hash lookup in this
   service's own database). No network call, no human JWT involved.

2. get_current_user_id / verify_facility_access / verify_asset_access /
   check_facility_role — for low-volume, human-driven management
   endpoints. Decode a real JWT and verify org membership (and
   optionally role) against auth-service/asset-service.
"""

import hashlib
from datetime import UTC, datetime

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.models.telemetry import EdgeDevice, IngestionKey
from common.roles import Role
from common.security import decode_and_verify_token

security = HTTPBearer()


def hash_key(raw_key: str) -> str:
    """Hash a raw ingestion key for storage/lookup. SHA-256 is sufficient
    here since keys are high-entropy random tokens, not human-guessable
    secrets — no need for bcrypt's deliberate slowness."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def verify_ingestion_key(
    x_ingestion_key: str = Header(..., alias="X-Ingestion-Key"),
    db: Session = Depends(get_db),
) -> EdgeDevice:
    """Verify a device API key locally and return its EdgeDevice."""
    key_hash = hash_key(x_ingestion_key)

    ingestion_key = (
        db.query(IngestionKey)
        .filter(IngestionKey.key_hash == key_hash, IngestionKey.revoked_at.is_(None))
        .first()
    )
    if ingestion_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked ingestion key",
        )

    device = ingestion_key.edge_device
    if device.deactivated_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Edge device is deactivated",
        )

    device.last_seen_at = datetime.now(UTC)
    db.commit()

    return device


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Decode and verify a human JWT locally. No network call."""
    user_id = decode_and_verify_token(
        credentials.credentials, settings.jwt_secret_key, settings.jwt_algorithm
    )
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return user_id


async def _check_facility_access(facility_id: str, token: str) -> str:
    """Core logic, callable directly with a raw token — for use inside
    route bodies where facility_id comes from a parsed request body."""
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
    if facility_resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this facility"
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
    """Depends()-compatible wrapper — only use where facility_id is a
    path/query parameter FastAPI can resolve automatically."""
    return await _check_facility_access(facility_id, credentials.credentials)


async def verify_asset_access(
    asset_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify the caller has org-level access to the asset, by asking
    asset-service (which itself resolves asset -> facility -> org and
    checks membership via auth-service)."""
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


async def check_facility_role(
    facility_id: str,
    credentials: HTTPAuthorizationCredentials,
    *allowed_roles: Role,
) -> str:
    """Core role-check logic, callable directly inside a route body.
    Resolves facility_id -> organization_id via asset-service, then
    checks the caller's role in that org via auth-service's
    GET /organizations (which returns role per org for the caller)."""
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
        if facility_resp.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this facility"
            )

        organization_id = facility_resp.json()["organization_id"]

        try:
            orgs_resp = await client.get(
                f"{settings.auth_service_url}/organizations",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="auth-service unavailable"
            ) from err

    if orgs_resp.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unexpected response from auth-service",
        )

    orgs = orgs_resp.json()
    matching_org = next((o for o in orgs if o["id"] == organization_id), None)
    if matching_org is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization"
        )

    if matching_org["role"] not in [r.value for r in allowed_roles]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of: {[r.value for r in allowed_roles]}",
        )

    user_id = decode_and_verify_token(token, settings.jwt_secret_key, settings.jwt_algorithm)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return user_id

"""Password hashing and JWT issuance for auth-service.

This is the ONLY service that issues tokens. Every other service only
verifies them, using common.security.decode_and_verify_token.
"""

from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage.

    Args:
        password: The user's plaintext password.

    Returns:
        A bcrypt hash safe to store in the database. The original password
        is never stored or recoverable from this hash.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored hash.

    Args:
        plain_password: Password submitted at login.
        hashed_password: The bcrypt hash stored on the User record.

    Returns:
        True if the password is correct, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    """Build and sign a JWT.

    Private helper (leading underscore) — not meant to be called directly
    from outside this module. Use create_access_token / create_refresh_token
    instead, which set the correct expiry and type for each use case.

    Args:
        subject: The user id this token identifies (goes in the "sub" claim).
        expires_delta: How long until this token expires.
        token_type: Either "access" or "refresh" — checked on verification
            so an access token can't be used where a refresh token is expected,
            or vice versa.

    Returns:
        A signed JWT string.
    """
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": subject, "exp": expire, "type": token_type}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    """Create a short-lived access token, sent with every authenticated request.

    Args:
        subject: The user id this token identifies.

    Returns:
        A signed JWT valid for settings.access_token_expire_minutes.
    """
    return _create_token(subject, timedelta(minutes=settings.access_token_expire_minutes), "access")


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh token, used only to obtain new access tokens.

    Args:
        subject: The user id this token identifies.

    Returns:
        A signed JWT valid for settings.refresh_token_expire_days.
    """
    return _create_token(subject, timedelta(days=settings.refresh_token_expire_days), "refresh")

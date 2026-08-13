"""Authentication endpoints: signup, login, and token refresh.

This is the entry point for every user's session — everything downstream
(organizations, and later every other service via common.security) depends
on tokens issued here being trustworthy.
"""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut
from common.security import decode_and_verify_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def signup(request: Request, payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user account.

    Args:
        request: Required by slowapi's rate-limit decorator (inspects
            the caller's IP via this) - not otherwise used in the body.
        payload: Signup fields — email, password, optional full name.
        db: Database session.

    Returns:
        The newly created User (without the password hash — UserOut excludes it).

    Raises:
        HTTPException: 400 if the email is already registered.

    Rate limited to 3/minute per IP - prevents automated mass account
    creation/spam while staying generous enough that a shared office/
    household network signing up several real users in quick succession
    won't get blocked. Like inference.py's confidence thresholds, this
    exact number is a reasonable, defensible starting point, not a
    validated-against-real-traffic constant - worth revisiting once
    real usage patterns exist.
    """
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Authenticate a user and issue a new access/refresh token pair.

    Args:
        request: Required by slowapi's rate-limit decorator.
        payload: Login credentials — email and password.
        db: Database session.

    Returns:
        A TokenPair (access_token + refresh_token).

    Raises:
        HTTPException: 401 if credentials are wrong, 403 if the account is deactivated.

    Rate limited to 5/minute per IP - the classic brute-force protection
    case this feature exists for. Generous enough that a real user who
    mistypes their password a couple of times isn't blocked, but bounds
    how fast a scripted attack can try passwords against one account
    from one source. Real, honest limitation (see main.py's comment on
    the Limiter): keyed on IP, not account - a distributed attack across
    many source IPs isn't stopped by this alone.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    # SQLAlchemy legacy Column() style: mypy sees Column[str] on instance
    # attribute access, not the real runtime str - same known limitation
    # as organizations.py.
    if not user or not verify_password(payload.password, cast(str, user.hashed_password)):
        # Deliberately identical error for "no such user" and "wrong password" —
        # revealing which one it was lets an attacker enumerate valid emails.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    # Same SQLAlchemy Column[str]-vs-str limitation as above.
    return TokenPair(
        access_token=create_access_token(cast(str, user.id)),
        refresh_token=create_refresh_token(cast(str, user.id)),
    )


@router.post("/refresh", response_model=TokenPair)
@limiter.limit("20/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Exchange a valid refresh token for a new access/refresh token pair.

    Args:
        request: Required by slowapi's rate-limit decorator.
        payload: Contains the refresh_token to exchange.
        db: Database session.

    Returns:
        A new TokenPair.

    Raises:
        HTTPException: 401 if the refresh token is invalid/expired, or the
            user no longer exists / is deactivated.

    Rate limited to 20/minute per IP - more generous than login/signup,
    since legitimate clients call this routinely (per this project's own
    apiFetch convention: refresh-on-401) rather than as a rare, deliberate
    action. Still bounded, in case a stolen refresh token gets hammered.
    """
    user_id = decode_and_verify_token(
        payload.refresh_token,
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        expected_type="refresh",
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    # Same SQLAlchemy Column[str]-vs-str limitation as above.
    return TokenPair(
        access_token=create_access_token(cast(str, user.id)),
        refresh_token=create_refresh_token(cast(str, user.id)),
    )

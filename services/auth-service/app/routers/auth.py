"""Authentication endpoints: signup, login, and token refresh.

This is the entry point for every user's session — everything downstream
(organizations, and later every other service via common.security) depends
on tokens issued here being trustworthy.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
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
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user account.

    Args:
        payload: Signup fields — email, password, optional full name.
        db: Database session.

    Returns:
        The newly created User (without the password hash — UserOut excludes it).

    Raises:
        HTTPException: 400 if the email is already registered.
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
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Authenticate a user and issue a new access/refresh token pair.

    Args:
        payload: Login credentials — email and password.
        db: Database session.

    Returns:
        A TokenPair (access_token + refresh_token).

    Raises:
        HTTPException: 401 if credentials are wrong, 403 if the account is deactivated.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Deliberately identical error for "no such user" and "wrong password" —
        # revealing which one it was lets an attacker enumerate valid emails.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    return TokenPair(
        access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id)
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Exchange a valid refresh token for a new access/refresh token pair.

    Args:
        payload: Contains the refresh_token to exchange.
        db: Database session.

    Returns:
        A new TokenPair.

    Raises:
        HTTPException: 401 if the refresh token is invalid/expired, or the
            user no longer exists / is deactivated.
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

    return TokenPair(
        access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id)
    )

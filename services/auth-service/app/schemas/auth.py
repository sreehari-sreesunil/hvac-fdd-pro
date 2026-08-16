from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import Role


class UserCreate(BaseModel):
    email: EmailStr
    # max_length=72 is not arbitrary - bcrypt (this project's password
    # hashing algorithm, see app/core/security.py) silently truncates
    # any input beyond 72 BYTES, meaning without this limit, two
    # different long passwords sharing the same first 72 bytes would
    # hash identically - a real, if obscure, security footgun, and the
    # exact class of bug already hit once this session (a bcrypt/
    # passlib version mismatch in a different context) - worth bounding
    # explicitly rather than relying on an obscure library behavior.
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=255)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    # Same max_length=72 reasoning as UserCreate.password - this is
    # compared against a stored bcrypt hash, so an unbounded input here
    # is also a real (if smaller) resource-exhaustion consideration on
    # every failed login attempt, not just at signup.
    password: str = Field(max_length=72)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class OrganizationCreate(BaseModel):
    name: str = Field(max_length=255)


class OrganizationOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    role: Role
    model_config = {"from_attributes": True}


class MemberInvite(BaseModel):
    email: EmailStr
    role: Role = Role.viewer


class MemberOut(BaseModel):
    user_id: str
    email: str
    role: Role

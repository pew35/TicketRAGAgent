"""User schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ....utils.tools import is_valid_email, normalize_email


class UserBase(BaseModel):
    """Shared user fields accepted by user API requests."""

    email: str = Field(min_length=3, max_length=255)
    display_name: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Normalize and validate email input before it reaches business logic."""
        email = normalize_email(value)
        if not is_valid_email(email):
            raise ValueError("Invalid email format.")
        return email


class UserCreate(UserBase):
    """Request body for creating a user account."""

    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Request body for updating editable user fields."""

    display_name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserLogin(BaseModel):
    """Request body for logging in with email and password."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Normalize and validate email input before authentication."""
        email = normalize_email(value)
        if not is_valid_email(email):
            raise ValueError("Invalid email format.")
        return email


class RefreshTokenRequest(BaseModel):
    """Request body for exchanging a refresh token for a new access token."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Token pair returned after login or token refresh."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = Field(
        default=None,
        description="Access token lifetime in seconds.",
    )


class UserPublic(BaseModel):
    """Safe user data returned by API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

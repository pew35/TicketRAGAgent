"""User API router for registration, login, profiles, and admin actions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....auth import get_current_superuser, get_current_user, verify_refresh_token
from ....dao import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    update_user,
)
from ....dependencies import get_db_session
from ....models import User
from ....utils.jwt import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    jwt_access_token_expire_minutes,
    verify_password,
)
from ..error_codes import ErrorCode
from ..response import ApiResponse, list_response, raise_api_error, success_response
from .schema import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
    UserUpdate,
)


router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
async def users_health() -> ApiResponse[dict[str, str]]:
    """Return user router health."""
    return success_response({"status": "ok", "router": "users"})


@router.post("/register", response_model=ApiResponse[UserPublic])
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[UserPublic]:
    """Register a new user account with a hashed password."""
    existing_user = await get_user_by_email(session, user_data.email)
    if existing_user is not None:
        raise_api_error(
            ErrorCode.EMAIL_ALREADY_REGISTERED,
            status_code=409,
        )

    user = await create_user(
        session,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        display_name=user_data.display_name,
    )
    await session.commit()
    return success_response(UserPublic.model_validate(user), message="User registered.")


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login_user(
    login_data: UserLogin,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[TokenResponse]:
    """Authenticate a user and return an access/refresh token pair."""
    user = await get_user_by_email(session, login_data.email)
    if user is None or not verify_password(login_data.password, user.hashed_password):
        raise_api_error(ErrorCode.INVALID_CREDENTIALS, status_code=401)

    if not user.is_active:
        raise_api_error(ErrorCode.INACTIVE_USER, status_code=403)

    return success_response(_build_token_response(user), message="Login successful.")


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[TokenResponse]:
    """Exchange a valid refresh token for a new token pair."""
    try:
        user_id = UUID(verify_refresh_token(refresh_data.refresh_token))
    except (HTTPException, ValueError):
        raise_api_error(ErrorCode.INVALID_REFRESH_TOKEN, status_code=401)

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise_api_error(ErrorCode.INVALID_REFRESH_TOKEN, status_code=401)

    return success_response(_build_token_response(user), message="Token refreshed.")


@router.get("/me", response_model=ApiResponse[UserPublic])
async def get_me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserPublic]:
    """Return the authenticated user's public profile."""
    return success_response(UserPublic.model_validate(current_user))


@router.get("/me/superuser", response_model=ApiResponse[UserPublic])
async def get_superuser_me(
    current_user: User = Depends(get_current_superuser),
) -> ApiResponse[UserPublic]:
    """Return the current user only when superuser authorization succeeds."""
    return success_response(UserPublic.model_validate(current_user))


@router.get("", response_model=ApiResponse[list[UserPublic]])
async def get_users(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_superuser),
) -> ApiResponse[list[UserPublic]]:
    """Return a paginated user list for superusers."""
    users = await list_users(session, limit=limit, offset=offset)
    return list_response(UserPublic.model_validate(user) for user in users)


@router.get("/{user_id}", response_model=ApiResponse[UserPublic])
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_superuser),
) -> ApiResponse[UserPublic]:
    """Return one user by id for superusers."""
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise_api_error(ErrorCode.USER_NOT_FOUND, status_code=404)

    return success_response(UserPublic.model_validate(user))


@router.patch("/{user_id}", response_model=ApiResponse[UserPublic])
async def patch_user(
    user_id: UUID,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_superuser),
) -> ApiResponse[UserPublic]:
    """Update editable user fields for superusers."""
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise_api_error(ErrorCode.USER_NOT_FOUND, status_code=404)

    updated_user = await update_user(
        session,
        user,
        display_name=user_data.display_name,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser,
    )
    await session.commit()
    return success_response(UserPublic.model_validate(updated_user))


@router.delete("/{user_id}", response_model=ApiResponse[None])
async def remove_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_superuser),
) -> ApiResponse[None]:
    """Delete one user account for superusers."""
    deleted = await delete_user(session, user_id)
    if not deleted:
        raise_api_error(ErrorCode.USER_NOT_FOUND, status_code=404)

    await session.commit()
    return success_response(message="User deleted.")


def _build_token_response(user: User) -> TokenResponse:
    """Create the token payload returned by login and refresh endpoints."""
    subject = str(user.id)
    extra_claims = {"email": user.email}
    return TokenResponse(
        access_token=create_access_token(subject, extra_claims=extra_claims),
        refresh_token=create_refresh_token(subject),
        expires_in=jwt_access_token_expire_minutes * 60,
    )

"""Authentication dependencies for protected FastAPI routes."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .dao import get_user_by_id
from .dependencies import get_db_session
from .models import User
from .utils.jwt import JWTDecodeError, decode_access_token, decode_refresh_token
from .web.api.error_codes import ErrorCode
from .web.api.response import raise_api_error


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Verify bearer access token and return the active authenticated user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized(
            "Missing bearer authentication credentials.",
            code=ErrorCode.AUTH_REQUIRED,
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(_get_subject(payload))
    except (JWTDecodeError, ValueError) as exc:
        raise unauthorized_error(
            "Invalid authentication token.",
            code=ErrorCode.INVALID_ACCESS_TOKEN,
        ) from exc

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise_unauthorized(
            "Authenticated user no longer exists.",
            code=ErrorCode.USER_NOT_FOUND,
        )

    if not user.is_active:
        raise_api_error(
            ErrorCode.INACTIVE_USER,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Inactive user account.",
        )

    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the current user only when the account has superuser access."""
    if not current_user.is_superuser:
        raise_api_error(
            ErrorCode.SUPERUSER_REQUIRED,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Superuser permission required.",
        )

    return current_user


def verify_refresh_token(token: str) -> str:
    """Verify a refresh token and return its subject user id."""
    try:
        payload = decode_refresh_token(token)
    except JWTDecodeError as exc:
        raise unauthorized_error(
            "Invalid refresh token.",
            code=ErrorCode.INVALID_REFRESH_TOKEN,
        ) from exc

    return _get_subject(payload)


def raise_unauthorized(
    detail: str = "Authentication failed.",
    *,
    code: ErrorCode = ErrorCode.AUTH_REQUIRED,
) -> None:
    """Raise a standard FastAPI 401 authentication error."""
    raise unauthorized_error(detail, code=code)


def unauthorized_error(
    detail: str = "Authentication failed.",
    *,
    code: ErrorCode = ErrorCode.AUTH_REQUIRED,
) -> HTTPException:
    """Create a standard FastAPI 401 authentication error."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": int(code),
            "message": detail,
            "data": None,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_subject(payload: dict[str, object]) -> str:
    """Extract and validate the token subject claim."""
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise JWTDecodeError("Token subject is missing.")

    return subject

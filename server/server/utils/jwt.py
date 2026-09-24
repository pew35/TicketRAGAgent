"""JWT token helpers for authentication workflows."""

from datetime import UTC, datetime, timedelta
import os
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

jwt_secret_key: str = os.getenv(
    "SERVER_JWT_SECRET_KEY",
    "ticket-rag-server-secret-key",
)
jwt_algorithm: str = "HS256"
jwt_access_token_expire_minutes: int = 60
jwt_refresh_token_expire_minutes: int = 24 * 60 * 7
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTDecodeError(ValueError):
    """Raised when a JWT token cannot be decoded or validated."""


def get_password_hash(password: str) -> str:
    """Hash a plain password before storing it in the database."""
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return whether a plain password matches the stored password hash."""
    return password_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed access token for one authenticated subject."""
    expire_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=jwt_access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "token_type": "access",
        "exp": expire_at,
        "iat": datetime.now(UTC),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        jwt_secret_key,
        algorithm=jwt_algorithm,
    )


def create_refresh_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed refresh token for renewing access tokens."""
    return create_access_token(
        subject,
        expires_delta=expires_delta
        or timedelta(minutes=jwt_refresh_token_expire_minutes),
        extra_claims={"token_type": "refresh", **(extra_claims or {})},
    )


def decode_token(
    token: str,
) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            jwt_secret_key,
            algorithms=[jwt_algorithm],
        )
    except JWTError as exc:
        raise JWTDecodeError("Invalid or expired token.") from exc

    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode a JWT token and require it to be an access token."""
    payload = decode_token(token)
    _require_token_type(payload, "access")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode a JWT token and require it to be a refresh token."""
    payload = decode_token(token)
    _require_token_type(payload, "refresh")
    return payload


def get_token_subject(
    token: str,
) -> str:
    """Return the subject stored in a JWT token."""
    payload = decode_token(token)
    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject:
        raise JWTDecodeError("Token subject is missing.")

    return subject


def _require_token_type(payload: dict[str, Any], expected_type: str) -> None:
    """Raise when a token payload has the wrong token type."""
    if payload.get("token_type") != expected_type:
        raise JWTDecodeError(f"Expected {expected_type} token.")

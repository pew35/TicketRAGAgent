"""Standard API response helpers."""

from collections.abc import Iterable
from typing import Any, Generic, NoReturn, TypeVar

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .error_codes import ErrorCode, get_error_message


DataT = TypeVar("DataT")
ItemT = TypeVar("ItemT")


class ApiResponse(BaseModel, Generic[DataT]):
    """Shared response shape returned by API endpoints."""

    code: int = Field(description="Application status code.")
    message: str = Field(description="Human-readable response message.")
    data: DataT | None = Field(default=None, description="Response payload.")


def success_response(
    data: DataT | None = None,
    *,
    message: str | None = None,
) -> ApiResponse[DataT]:
    """Build a successful API response."""
    return ApiResponse(
        code=ErrorCode.SUCCESS,
        message=message or get_error_message(ErrorCode.SUCCESS),
        data=data,
    )


def list_response(
    data: Iterable[ItemT] | None = None,
    *,
    message: str | None = None,
) -> ApiResponse[list[ItemT]]:
    """Build a successful list API response, using an empty list for no results."""
    return ApiResponse(
        code=ErrorCode.SUCCESS,
        message=message or get_error_message(ErrorCode.SUCCESS),
        data=list(data) if data is not None else [],
    )


def error_response(
    code: ErrorCode | int,
    *,
    message: str | None = None,
    data: Any | None = None,
) -> ApiResponse[Any]:
    """Build a failed API response."""
    return ApiResponse(
        code=int(code),
        message=message or get_error_message(code),
        data=data,
    )


def raise_api_error(
    code: ErrorCode | int,
    *,
    status_code: int,
    message: str | None = None,
    data: Any | None = None,
    headers: dict[str, str] | None = None,
) -> NoReturn:
    """Raise an HTTPException carrying the precise application error response."""
    raise HTTPException(
        status_code=status_code,
        detail=error_response(code, message=message, data=data).model_dump(),
        headers=headers,
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Convert FastAPI HTTPException into the standard API response shape."""
    response = _response_from_http_exception(exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(response.model_dump()),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convert request validation errors into the standard API response shape."""
    response = error_response(
        ErrorCode.VALIDATION_ERROR,
        data={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(response.model_dump()),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert unexpected server errors into the standard API response shape."""
    response = error_response(ErrorCode.INTERNAL_ERROR)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(response.model_dump()),
    )


def _error_code_from_http_status(status_code: int) -> ErrorCode:
    """Map common HTTP status codes to application error codes."""
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return ErrorCode.AUTH_REQUIRED
    if status_code == status.HTTP_403_FORBIDDEN:
        return ErrorCode.PERMISSION_DENIED
    if status_code == status.HTTP_404_NOT_FOUND:
        return ErrorCode.RESOURCE_NOT_FOUND
    if status_code == status.HTTP_409_CONFLICT:
        return ErrorCode.RESOURCE_CONFLICT
    if status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        return ErrorCode.REQUEST_TOO_LARGE
    if status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
        return ErrorCode.UNSUPPORTED_MEDIA_TYPE
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return ErrorCode.RATE_LIMITED

    return ErrorCode.BAD_REQUEST


def _response_from_http_exception(exc: HTTPException) -> ApiResponse[Any]:
    """Build a response from HTTPException detail, preserving precise app codes."""
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code")
        message = exc.detail.get("message")
        data = exc.detail.get("data")
        if code is not None:
            return error_response(
                int(code),
                message=str(message) if message is not None else None,
                data=data,
            )

    code = _error_code_from_http_status(exc.status_code)
    return error_response(code, message=str(exc.detail))

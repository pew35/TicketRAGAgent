"""Monitoring routes for service health and dependency readiness."""

from time import perf_counter

import httpx
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ....dependencies import (
    get_app_settings,
    get_cloud_agent,
    get_db_session,
    get_redis_client,
)
from ....services.cloud_agent import CloudTicketAgent
from ....settings import Settings
from ..error_codes import ErrorCode
from ..response import ApiResponse, success_response


router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
async def health_check() -> ApiResponse[dict[str, str]]:
    """Return API health status."""
    return success_response({"status": "ok", "service": "server"})


@router.get("/settings", response_model=ApiResponse[dict[str, str | int | bool]])
async def settings_summary(
    settings: Settings = Depends(get_app_settings),
) -> ApiResponse[dict[str, str | int | bool]]:
    """Return non-secret runtime settings useful during development."""
    return success_response(
        {
            "app_name": settings.app_name,
            "environment": settings.environment,
            "debug": settings.debug,
            "host": settings.host,
            "port": settings.port,
            "agent_base_url": settings.agent_base_url,
        }
    )


@router.get("/readiness", response_model=ApiResponse[dict])
async def readiness_check(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis | None = Depends(get_redis_client),
    settings: Settings = Depends(get_app_settings),
    cloud_agent: CloudTicketAgent | None = Depends(get_cloud_agent),
) -> ApiResponse[dict]:
    """Check database, Redis, and agent-service connectivity."""
    started_at = perf_counter()
    checks = {
        "database": await _check_database(session),
        "redis": await _check_redis(redis, settings),
        "agent": await _check_agent(settings, cloud_agent),
    }
    ready = all(check["ok"] for check in checks.values())
    return success_response(
        {
            "ready": ready,
            "checks": checks,
            "elapsed_ms": int((perf_counter() - started_at) * 1000),
        }
    )


async def _check_database(session: AsyncSession) -> dict[str, object]:
    """Run a tiny SQL query to verify database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        return {
            "ok": False,
            "code": int(ErrorCode.DATABASE_CONNECTION_FAILED),
            "message": str(exc),
        }
    return {"ok": True, "code": int(ErrorCode.SUCCESS), "message": "ok"}


async def _check_redis(
    redis: Redis | None,
    settings: Settings,
) -> dict[str, object]:
    """Ping Redis to verify cache connectivity."""
    if not settings.redis_enabled:
        return {"ok": True, "code": int(ErrorCode.SUCCESS), "message": "disabled"}
    if redis is None:
        return {
            "ok": False,
            "code": int(ErrorCode.REDIS_CONNECTION_FAILED),
            "message": "Redis client was not initialized.",
        }
    try:
        await redis.ping()
    except Exception as exc:
        return {
            "ok": False,
            "code": int(ErrorCode.REDIS_CONNECTION_FAILED),
            "message": str(exc),
        }
    return {"ok": True, "code": int(ErrorCode.SUCCESS), "message": "ok"}


async def _check_agent(
    settings: Settings,
    cloud_agent: CloudTicketAgent | None,
) -> dict[str, object]:
    """Call the agent health endpoint to verify agent-service connectivity."""
    if settings.agent_mode.lower() == "internal":
        return {
            "ok": bool(cloud_agent and cloud_agent.ready),
            "code": int(
                ErrorCode.SUCCESS
                if cloud_agent and cloud_agent.ready
                else ErrorCode.AGENT_SERVICE_UNAVAILABLE
            ),
            "message": "ok" if cloud_agent and cloud_agent.ready else "not ready",
        }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.agent_base_url}/health")
            response.raise_for_status()
    except Exception as exc:
        return {
            "ok": False,
            "code": int(ErrorCode.AGENT_SERVICE_UNAVAILABLE),
            "message": str(exc),
        }

    return {"ok": True, "code": int(ErrorCode.SUCCESS), "message": "ok"}

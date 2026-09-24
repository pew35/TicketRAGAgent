"""Reusable FastAPI dependencies for request handlers."""

from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .services.redis import get_redis
from .services.cloud_agent import CloudTicketAgent
from .settings import Settings, get_settings


def get_app_settings() -> Settings:
    """Return cached application settings for dependency injection."""
    return get_settings()


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield one database session from the app session factory."""
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        yield session


def get_redis_client(request: Request) -> Redis:
    """Return the shared Redis client for route dependencies."""
    return get_redis(request)


def get_cloud_agent(request: Request) -> CloudTicketAgent | None:
    """Return the in-process cloud agent when deployment mode enables it."""
    return getattr(request.app.state, "cloud_agent", None)

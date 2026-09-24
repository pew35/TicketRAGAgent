"""Redis lifecycle hooks for FastAPI application startup and shutdown."""

from fastapi import FastAPI
from redis.asyncio import Redis

from ...settings import Settings
from .client import create_redis_client


def init_redis(app: FastAPI, settings: Settings) -> Redis:
    """Initialize the shared Redis client and attach it to app state."""
    redis = create_redis_client(settings)
    app.state.redis = redis

    return redis


async def shutdown_redis(app: FastAPI) -> None:
    """Close the shared Redis client if it was initialized."""
    redis: Redis | None = getattr(app.state, "redis", None)
    if redis is None:
        return

    await close_redis(redis)
    app.state.redis = None


async def close_redis(redis: Redis) -> None:
    """Close Redis clients across redis-py versions."""
    if hasattr(redis, "aclose"):
        await redis.aclose()
        return

    await redis.close()

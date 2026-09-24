"""FastAPI dependencies for Redis access."""

from fastapi import Request
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    """Return the shared Redis client stored on FastAPI app state."""
    return request.app.state.redis

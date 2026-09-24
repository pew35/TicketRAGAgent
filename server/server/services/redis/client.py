"""Redis client construction helpers."""

from redis.asyncio import Redis

from ...settings import Settings


def create_redis_client(settings: Settings) -> Redis:
    """Create a Redis client from application settings."""
    return Redis.from_url(str(settings.redis_url), decode_responses=True)

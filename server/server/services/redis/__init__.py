"""Redis service helpers for cache and shared runtime state."""

from .dependency import get_redis
from .lifetime import init_redis, shutdown_redis


__all__ = ["get_redis", "init_redis", "shutdown_redis"]

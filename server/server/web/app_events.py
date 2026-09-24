"""Application lifecycle events for the FastAPI server."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from ..db_utils import create_engine, create_session_factory
from ..logging import get_logger
from ..services.redis import init_redis, shutdown_redis
from ..services.cloud_agent import CloudTicketAgent
from ..settings import Settings


def _setup_db(app: FastAPI, settings: Settings) -> AsyncEngine:
    """Create the database engine and session factory for the application."""
    engine = create_engine(settings)
    app.state.db_engine = engine
    app.state.db_session_factory = create_session_factory(engine)

    return engine


def create_lifespan(settings: Settings):
    """Create the FastAPI lifespan handler using application settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Initialize and dispose shared application resources."""
        logger = get_logger()
        engine = _setup_db(app, settings)
        app.state.redis = None
        if settings.redis_enabled:
            init_redis(app, settings)
        app.state.cloud_agent = None
        if settings.agent_mode.lower() == "internal":
            app.state.cloud_agent = CloudTicketAgent(settings)
        logger.info(
            "Application resources initialized: database={}:{} redis_enabled={} agent_mode={}",
            settings.db_host,
            settings.db_port,
            settings.redis_enabled,
            settings.agent_mode,
        )

        try:
            yield
        finally:
            await shutdown_redis(app)
            await engine.dispose()
            logger.info("Application resources disposed")

    return lifespan

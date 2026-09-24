"""Database engine, session factory, and schema management utilities."""

import argparse
import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .logging import get_logger
from .models import Base
from .settings import Settings, get_settings


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create the async SQLAlchemy engine from application settings."""
    active_settings = settings or get_settings()
    return create_async_engine(
        str(active_settings.db_url),
        echo=active_settings.debug,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create the async SQLAlchemy session factory."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield one database session and close it after use."""
    async with session_factory() as session:
        yield session


async def create_tables(settings: Settings | None = None) -> None:
    """Create all database tables registered on SQLAlchemy metadata."""
    logger = get_logger()
    engine = create_engine(settings)
    _import_models()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await engine.dispose()
    logger.info("Database tables created")


async def drop_tables(settings: Settings | None = None) -> None:
    """Drop all database tables registered on SQLAlchemy metadata."""
    logger = get_logger()
    engine = create_engine(settings)
    _import_models()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    logger.warning("Database tables dropped")


async def recreate_tables(settings: Settings | None = None) -> None:
    """Drop and recreate all database tables."""
    await drop_tables(settings)
    await create_tables(settings)


def _import_models() -> None:
    """Import ORM models so they are registered on Base.metadata."""
    from . import models  # noqa: F401


def main() -> None:
    """Run database schema management commands from the command line."""
    parser = argparse.ArgumentParser(description="Manage database tables.")
    parser.add_argument(
        "command",
        choices=("create", "drop", "recreate"),
        help="Database schema command to run.",
    )
    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(create_tables())
    elif args.command == "drop":
        asyncio.run(drop_tables())
    elif args.command == "recreate":
        asyncio.run(recreate_tables())


if __name__ == "__main__":
    main()

"""Logging configuration for the Ticket RAG server."""

import logging as std_logging
import sys
from typing import Any

from loguru import logger

from .settings import LogLevel
from .settings import Settings, get_settings


def record_formatter(record: dict[str, Any]) -> str:
    """Return the Loguru format string for one log record."""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>\n{exception}"
    )


class InterceptHandler(std_logging.Handler):
    """Forward standard logging records into Loguru."""

    def emit(self, record: std_logging.LogRecord) -> None:
        """Convert a standard logging record into a Loguru record."""
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = std_logging.currentframe(), 2
        while frame and frame.f_code.co_filename == std_logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def configure_logging(settings: Settings | None = None) -> None:
    """Configure Loguru and redirect framework logs through it."""
    active_settings = settings or get_settings()
    log_level = _normalize_log_level(active_settings.log_level)

    # Replace Loguru's default sink so the whole app uses one consistent format.
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format=record_formatter,
        colorize=True,
        backtrace=active_settings.debug,
        diagnose=active_settings.debug,
    )

    # Route standard logging, including Uvicorn/FastAPI internals, into Loguru.
    std_logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in _framework_logger_names():
        framework_logger = std_logging.getLogger(logger_name)
        framework_logger.handlers = [InterceptHandler()]
        framework_logger.propagate = False


def _framework_logger_names() -> tuple[str, ...]:
    """Return framework logger names that should share the app log format."""
    return (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
    )


def _normalize_log_level(log_level: LogLevel) -> str | int:
    """Convert configured log level values into Loguru-compatible levels."""
    if log_level is LogLevel.notset:
        return 0
    if log_level is LogLevel.fatal:
        return "CRITICAL"
    return log_level.value


def get_logger() -> Any:
    """Return the configured Loguru logger instance."""
    return logger

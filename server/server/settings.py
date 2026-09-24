"""Application settings loaded from environment variables."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL


class LogLevel(str, Enum):
    """Supported application logging levels."""

    notset = "NOTSET"
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    fatal = "FATAL"


class Settings(BaseSettings):
    """Typed server configuration values."""

    app_name: str = "Ticket RAG Server"
    environment: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level: LogLevel = LogLevel.info
    temp_dir: Path = Path(gettempdir())

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "server"
    db_pass: str = "server"
    db_base: str = "server"
    database_url: str | None = None

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_user: str | None = None
    redis_pass: str | None = "server"
    redis_base: int | None = None
    redis_enabled: bool = True

    agent_base_url: str = "http://localhost:8001"
    agent_mode: str = "http"
    ticket_data_path: Path = (
        Path(__file__).resolve().parents[2] / "agent" / "data" / "service_tickets.csv"
    )
    llm_api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    llm_api_key: str | None = None
    llm_model: str = "openrouter/free"
    llm_site_url: str | None = None
    llm_site_name: str = "TicketRAGAgent"
    frontend_dist_dir: Path = (
        Path(__file__).resolve().parents[2] / "frontend" / "dist"
    )

    cors_allow_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SERVER_",
        extra="ignore",
    )

    @field_validator("redis_user", "redis_pass", mode="before")
    @classmethod
    def _empty_string_to_none(cls, value: str | None) -> str | None:
        """Treat empty Redis credentials from .env as no credential."""
        if value == "":
            return None
        return value

    @property
    def debug(self) -> bool:
        """Return whether debug mode should be enabled."""
        return self.environment.lower() in {"dev", "local", "development"}

    @property
    def db_url(self) -> URL:
        """Build the async PostgreSQL connection URL."""
        if self.database_url:
            database_url = self.database_url
            if database_url.startswith("postgres://"):
                database_url = database_url.replace(
                    "postgres://", "postgresql+asyncpg://", 1
                )
            elif database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )
            url = URL(database_url)
            query = dict(url.query)
            if "sslmode" in query and "ssl" not in query:
                query["ssl"] = query.pop("sslmode")
            query.pop("channel_binding", None)
            return url.with_query(query)

        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_base}",
        )

    @property
    def redis_url(self) -> URL:
        """Build the Redis connection URL."""
        path = "/0"
        if self.redis_base is not None:
            path = f"/{self.redis_base}"

        return URL.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            user=self.redis_user,
            password=self.redis_pass,
            path=path,
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

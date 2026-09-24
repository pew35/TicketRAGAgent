"""Agent run ORM model for future observability and debugging."""

from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentRunStatus(str, Enum):
    """Allowed lifecycle states for one Agent request."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Technical record of one call from server to the Agent service."""

    __tablename__ = "agent_runs"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id"),
        index=True,
    )
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        SqlEnum(AgentRunStatus, native_enum=False),
        default=AgentRunStatus.pending,
        nullable=False,
    )
    status_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship(back_populates="agent_runs")
    conversation: Mapped["Conversation"] = relationship(back_populates="agent_runs")

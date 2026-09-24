"""Conversation and message ORM models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .agent_run import AgentRun
    from .user import User


class MessageRole(str, Enum):
    """Allowed conversation message roles."""

    user = "user"
    assistant = "assistant"
    system = "system"


class MessageStatus(str, Enum):
    """Allowed lifecycle states for a stored message."""

    pending = "pending"
    streaming = "streaming"
    completed = "completed"
    failed = "failed"


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A chat thread owned by one user."""

    __tablename__ = "conversations"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="New Chat")
    last_message_preview: Mapped[str | None] = mapped_column(String(240), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.sequence",
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One message inside a conversation."""

    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence",
            name="uq_conversation_messages_conversation_sequence",
        ),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id"),
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SqlEnum(MessageRole, native_enum=False),
        nullable=False,
    )
    status: Mapped[MessageStatus] = mapped_column(
        SqlEnum(MessageStatus, native_enum=False),
        default=MessageStatus.completed,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

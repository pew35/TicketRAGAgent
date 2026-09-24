"""Conversation and message schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ....models import MessageRole, MessageStatus


class ConversationCreate(BaseModel):
    """Request body for creating a conversation."""

    title: str | None = Field(default=None, max_length=160)


class ConversationUpdate(BaseModel):
    """Request body for updating a conversation title."""

    title: str = Field(min_length=1, max_length=160)


class ConversationPublic(BaseModel):
    """Conversation data returned by API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    last_message_preview: str | None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    """Request body for sending a user message to the agent."""

    content: str = Field(min_length=1)


class MessagePublic(BaseModel):
    """Message data returned by API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: MessageRole
    status: MessageStatus
    sequence: int
    content: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    """Conversation detail response including its messages."""

    conversation: ConversationPublic
    messages: list[MessagePublic]


class AgentAnswerData(BaseModel):
    """Stored result after a non-streaming message request finishes."""

    user_message: MessagePublic
    assistant_message: MessagePublic
    answer: str
    sources: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


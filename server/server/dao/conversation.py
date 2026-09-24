"""Conversation and message database access helpers."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Conversation,
    ConversationMessage,
    MessageRole,
    MessageStatus,
)


async def create_conversation(
    session: AsyncSession,
    *,
    user_id: UUID,
    title: str = "New Chat",
) -> Conversation:
    """Create a conversation owned by one user."""
    conversation = Conversation(user_id=user_id, title=title)
    session.add(conversation)
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def get_conversation_by_id(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID | None = None,
    include_deleted: bool = False,
) -> Conversation | None:
    """Return one conversation, optionally scoped to a user."""
    statement = select(Conversation).where(Conversation.id == conversation_id)

    if user_id is not None:
        statement = statement.where(Conversation.user_id == user_id)

    if not include_deleted:
        statement = statement.where(Conversation.deleted_at.is_(None))

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def list_user_conversations(
    session: AsyncSession,
    *,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False,
) -> list[Conversation]:
    """List conversations for one user, newest first."""
    statement = select(Conversation).where(Conversation.user_id == user_id)

    if not include_deleted:
        statement = statement.where(Conversation.deleted_at.is_(None))

    statement = (
        statement.order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def update_conversation_title(
    session: AsyncSession,
    conversation: Conversation,
    *,
    title: str,
) -> Conversation:
    """Update a conversation title."""
    conversation.title = title
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def soft_delete_conversation(
    session: AsyncSession,
    conversation: Conversation,
) -> Conversation:
    """Mark a conversation as deleted without removing its records."""
    conversation.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def get_next_message_sequence(
    session: AsyncSession,
    *,
    conversation_id: UUID,
) -> int:
    """Return the next message sequence number for one conversation."""
    result = await session.execute(
        select(func.coalesce(func.max(ConversationMessage.sequence), 0)).where(
            ConversationMessage.conversation_id == conversation_id,
        )
    )
    return int(result.scalar_one()) + 1


async def create_message(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    role: MessageRole,
    content: str,
    sequence: int | None = None,
    status: MessageStatus = MessageStatus.completed,
) -> ConversationMessage:
    """Create one message inside a conversation."""
    if sequence is None:
        sequence = await get_next_message_sequence(
            session,
            conversation_id=conversation_id,
        )

    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sequence=sequence,
        status=status,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    await _update_conversation_preview(session, conversation_id, content)
    return message


async def list_conversation_messages(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[ConversationMessage]:
    """List messages for one conversation in display order."""
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.sequence.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def _update_conversation_preview(
    session: AsyncSession,
    conversation_id: UUID,
    content: str,
) -> None:
    """Update the conversation preview after a new message is saved."""
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        return

    conversation.last_message_preview = content[:240]
    await session.flush()

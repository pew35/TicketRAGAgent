"""Agent run database access helpers."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AgentRun, AgentRunStatus


async def create_agent_run(
    session: AsyncSession,
    *,
    user_id: UUID,
    conversation_id: UUID,
    question: str,
    model_name: str | None = None,
    extra_data: dict[str, Any] | None = None,
) -> AgentRun:
    """Create a pending Agent run record."""
    agent_run = AgentRun(
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        model_name=model_name,
        extra_data=extra_data,
    )
    session.add(agent_run)
    await session.flush()
    await session.refresh(agent_run)
    return agent_run


async def get_agent_run_by_id(
    session: AsyncSession,
    *,
    agent_run_id: UUID,
    user_id: UUID | None = None,
) -> AgentRun | None:
    """Return one Agent run, optionally scoped to a user."""
    statement = select(AgentRun).where(AgentRun.id == agent_run_id)

    if user_id is not None:
        statement = statement.where(AgentRun.user_id == user_id)

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def mark_agent_run_success(
    session: AsyncSession,
    agent_run: AgentRun,
    *,
    answer: str,
    latency_ms: int | None = None,
    status_code: str | None = None,
    extra_data: dict[str, Any] | None = None,
) -> AgentRun:
    """Mark an Agent run as completed."""
    agent_run.answer = answer
    agent_run.latency_ms = latency_ms
    agent_run.status_code = status_code
    agent_run.status = AgentRunStatus.completed

    if extra_data is not None:
        agent_run.extra_data = extra_data

    await session.flush()
    await session.refresh(agent_run)
    return agent_run


async def mark_agent_run_failed(
    session: AsyncSession,
    agent_run: AgentRun,
    *,
    error_message: str,
    latency_ms: int | None = None,
    status_code: str | None = None,
    extra_data: dict[str, Any] | None = None,
) -> AgentRun:
    """Mark an Agent run as failed."""
    agent_run.error_message = error_message
    agent_run.latency_ms = latency_ms
    agent_run.status_code = status_code
    agent_run.status = AgentRunStatus.failed

    if extra_data is not None:
        agent_run.extra_data = extra_data

    await session.flush()
    await session.refresh(agent_run)
    return agent_run

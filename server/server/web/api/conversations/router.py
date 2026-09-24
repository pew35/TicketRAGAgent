"""Conversation API router for chat history and agent-backed messages."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from time import perf_counter
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....auth import get_current_user
from ....dao import (
    create_agent_run,
    create_conversation,
    create_message,
    get_conversation_by_id,
    list_conversation_messages,
    list_user_conversations,
    mark_agent_run_failed,
    mark_agent_run_success,
    soft_delete_conversation,
    update_conversation_title,
)
from ....dependencies import get_app_settings, get_cloud_agent, get_db_session
from ....models import MessageRole, MessageStatus, User
from ....services.cloud_agent import CloudTicketAgent
from ....settings import Settings
from ..error_codes import ErrorCode
from ..response import (
    ApiResponse,
    error_response,
    list_response,
    raise_api_error,
    success_response,
)
from .schema import (
    AgentAnswerData,
    ConversationCreate,
    ConversationDetail,
    ConversationPublic,
    ConversationUpdate,
    MessageCreate,
    MessagePublic,
)


router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
async def conversations_health() -> ApiResponse[dict[str, str]]:
    """Return conversation router health."""
    return success_response({"status": "ok", "router": "conversations"})


@router.post("", response_model=ApiResponse[ConversationPublic])
async def create_chat_conversation(
    conversation_data: ConversationCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ConversationPublic]:
    """Create a new chat conversation for the current user."""
    title = conversation_data.title or "New Chat"
    conversation = await create_conversation(
        session,
        user_id=current_user.id,
        title=title,
    )
    await session.commit()
    return success_response(ConversationPublic.model_validate(conversation))


@router.get("", response_model=ApiResponse[list[ConversationPublic]])
async def get_chat_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[ConversationPublic]]:
    """List conversations owned by the current user."""
    conversations = await list_user_conversations(
        session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return list_response(
        ConversationPublic.model_validate(conversation)
        for conversation in conversations
    )


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationDetail])
async def get_chat_conversation(
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ConversationDetail]:
    """Return one conversation and its messages."""
    conversation = await get_conversation_by_id(
        session,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise_api_error(ErrorCode.CONVERSATION_NOT_FOUND, status_code=404)

    messages = await list_conversation_messages(
        session,
        conversation_id=conversation.id,
        limit=limit,
        offset=offset,
    )
    return success_response(
        ConversationDetail(
            conversation=ConversationPublic.model_validate(conversation),
            messages=[
                MessagePublic.model_validate(message)
                for message in messages
            ],
        )
    )


@router.patch("/{conversation_id}", response_model=ApiResponse[ConversationPublic])
async def patch_chat_conversation(
    conversation_id: UUID,
    conversation_data: ConversationUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ConversationPublic]:
    """Update a conversation title."""
    conversation = await get_conversation_by_id(
        session,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise_api_error(ErrorCode.CONVERSATION_NOT_FOUND, status_code=404)

    conversation = await update_conversation_title(
        session,
        conversation,
        title=conversation_data.title,
    )
    await session.commit()
    return success_response(ConversationPublic.model_validate(conversation))


@router.delete("/{conversation_id}", response_model=ApiResponse[None])
async def delete_chat_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[None]:
    """Soft delete a conversation owned by the current user."""
    conversation = await get_conversation_by_id(
        session,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise_api_error(ErrorCode.CONVERSATION_NOT_FOUND, status_code=404)

    await soft_delete_conversation(session, conversation)
    await session.commit()
    return success_response(message="Conversation deleted.")


@router.get("/{conversation_id}/messages", response_model=ApiResponse[list[MessagePublic]])
async def get_chat_messages(
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[MessagePublic]]:
    """List messages in a conversation owned by the current user."""
    conversation = await get_conversation_by_id(
        session,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise_api_error(ErrorCode.CONVERSATION_NOT_FOUND, status_code=404)

    messages = await list_conversation_messages(
        session,
        conversation_id=conversation.id,
        limit=limit,
        offset=offset,
    )
    return list_response(MessagePublic.model_validate(message) for message in messages)


@router.post("/{conversation_id}/messages", response_model=ApiResponse[AgentAnswerData])
async def create_chat_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings),
    cloud_agent: CloudTicketAgent | None = Depends(get_cloud_agent),
) -> ApiResponse[AgentAnswerData]:
    """Create a user message, call the agent once, and store the answer."""
    conversation = await get_conversation_by_id(
        session,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise_api_error(ErrorCode.CONVERSATION_NOT_FOUND, status_code=404)

    user_message = await create_message(
        session,
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=message_data.content,
    )
    agent_run = await create_agent_run(
        session,
        user_id=current_user.id,
        conversation_id=conversation.id,
        question=message_data.content,
    )
    await session.commit()

    started_at = perf_counter()
    try:
        agent_data = await _ask_agent(
            settings,
            message_data.content,
            cloud_agent=cloud_agent,
        )
    except httpx.TimeoutException:
        await mark_agent_run_failed(
            session,
            agent_run,
            error_message="Agent service request timed out.",
            latency_ms=_elapsed_ms(started_at),
            status_code=str(int(ErrorCode.AGENT_SERVICE_TIMEOUT)),
        )
        await create_message(
            session,
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content="Agent service timed out.",
            status=MessageStatus.failed,
        )
        await session.commit()
        raise_api_error(
            ErrorCode.AGENT_SERVICE_TIMEOUT,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except (httpx.HTTPError, ValueError) as exc:
        await mark_agent_run_failed(
            session,
            agent_run,
            error_message=str(exc),
            latency_ms=_elapsed_ms(started_at),
            status_code=str(_agent_error_code(exc)),
        )
        await create_message(
            session,
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content="Agent service returned an invalid response.",
            status=MessageStatus.failed,
        )
        await session.commit()
        raise_api_error(
            _agent_error_code(exc),
            status_code=_agent_http_status(exc),
        )

    answer = str(agent_data.get("answer") or "")
    sources = _list_or_empty(agent_data.get("sources"))
    metadata = _dict_or_empty(agent_data.get("metadata"))
    assistant_message = await create_message(
        session,
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=answer,
    )
    await mark_agent_run_success(
        session,
        agent_run,
        answer=answer,
        latency_ms=_elapsed_ms(started_at),
        status_code=str(agent_data.get("code", int(ErrorCode.SUCCESS))),
        extra_data={"sources": sources, "metadata": metadata},
    )
    await _set_initial_title(
        session,
        conversation,
        message_data.content,
        settings,
        cloud_agent,
    )
    await session.commit()

    return success_response(
        AgentAnswerData(
            user_message=MessagePublic.model_validate(user_message),
            assistant_message=MessagePublic.model_validate(assistant_message),
            answer=answer,
            sources=sources,
            metadata=metadata,
        )
    )


@router.post("/{conversation_id}/messages/stream")
async def create_chat_message_stream(
    conversation_id: UUID,
    message_data: MessageCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings),
    cloud_agent: CloudTicketAgent | None = Depends(get_cloud_agent),
) -> StreamingResponse:
    """Create a user message and stream the agent answer as server-sent events."""
    conversation = await get_conversation_by_id(
        session,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise_api_error(ErrorCode.CONVERSATION_NOT_FOUND, status_code=404)

    user_message = await create_message(
        session,
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=message_data.content,
    )
    agent_run = await create_agent_run(
        session,
        user_id=current_user.id,
        conversation_id=conversation.id,
        question=message_data.content,
    )
    await session.commit()

    async def event_generator() -> AsyncGenerator[str, None]:
        answer_parts: list[str] = []
        sources: list[dict] = []
        metadata: dict = {}
        started_at = perf_counter()

        try:
            async for event in _stream_agent_events(
                settings,
                message_data.content,
                cloud_agent=cloud_agent,
            ):
                event_type = str(event.get("type") or "message")
                data = event.get("data") if isinstance(event.get("data"), dict) else {}
                content = str(event.get("content") or "")

                if event_type == "token":
                    answer_parts.append(content)
                elif event_type == "sources":
                    sources = _list_or_empty(data.get("sources"))
                elif event_type == "done":
                    metadata = _dict_or_empty(data)

                yield _format_sse(event_type, event)

            answer = "".join(answer_parts)
            assistant_message = await create_message(
                session,
                conversation_id=conversation.id,
                role=MessageRole.assistant,
                content=answer,
            )
            await mark_agent_run_success(
                session,
                agent_run,
                answer=answer,
                latency_ms=_elapsed_ms(started_at),
                status_code=str(int(ErrorCode.SUCCESS)),
                extra_data={"sources": sources, "metadata": metadata},
            )
            await _set_initial_title(
                session,
                conversation,
                message_data.content,
                settings,
                cloud_agent,
            )
            await session.commit()
            yield _format_sse(
                "stored",
                success_response(
                    {
                        "user_message_id": str(user_message.id),
                        "assistant_message_id": str(assistant_message.id),
                    }
                ).model_dump(),
            )
        except httpx.TimeoutException:
            await _store_stream_failure(
                session,
                conversation.id,
                agent_run,
                "Agent service request timed out.",
                started_at,
                ErrorCode.AGENT_SERVICE_TIMEOUT,
            )
            yield _format_sse(
                "error",
                error_response(ErrorCode.AGENT_SERVICE_TIMEOUT).model_dump(),
            )
        except (httpx.HTTPError, ValueError) as exc:
            await _store_stream_failure(
                session,
                conversation.id,
                agent_run,
                str(exc),
                started_at,
                _agent_error_code(exc),
            )
            yield _format_sse(
                "error",
                error_response(_agent_error_code(exc)).model_dump(),
            )

    return _sse_response(event_generator())


async def _ask_agent(
    settings: Settings,
    question: str,
    *,
    timeout: float = 60.0,
    cloud_agent: CloudTicketAgent | None = None,
) -> dict:
    """Call the agent HTTP service for one complete answer."""
    if cloud_agent is not None:
        return await cloud_agent.answer(question)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{settings.agent_base_url}/api/ask",
            json={"question": question},
        )
        response.raise_for_status()
        payload = response.json()

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if int(payload.get("code", 0)) != int(ErrorCode.SUCCESS):
        raise httpx.HTTPStatusError(
            "Agent returned an application error.",
            request=response.request,
            response=response,
        )
    return data


async def _stream_agent_events(
    settings: Settings,
    question: str,
    *,
    cloud_agent: CloudTicketAgent | None = None,
) -> AsyncGenerator[dict, None]:
    """Read newline-delimited agent events from the agent service."""
    if cloud_agent is not None:
        async for event in cloud_agent.stream_answer(question):
            yield event
        return

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{settings.agent_base_url}/api/ask/stream",
            json={"question": question},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                yield json.loads(line)


async def _set_initial_title(
    session: AsyncSession,
    conversation,
    question: str,
    settings: Settings,
    cloud_agent: CloudTicketAgent | None = None,
) -> None:
    """Generate a compact LLM title for the first user question."""
    if conversation.title != "New Chat":
        return

    title = await _generate_conversation_title(settings, question, cloud_agent)
    if not title:
        title = _fallback_title(question)

    await update_conversation_title(session, conversation, title=title)


async def _generate_conversation_title(
    settings: Settings,
    question: str,
    cloud_agent: CloudTicketAgent | None = None,
) -> str:
    """Ask the agent service to summarize a user question into a short title."""
    if cloud_agent is not None:
        return _clean_generated_title(
            await cloud_agent.generate_title(question, max_length=40)
        )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{settings.agent_base_url}/api/title",
                json={"question": question, "max_length": 40},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return ""

    title = str(data.get("title") or "")
    return _clean_generated_title(title)


def _clean_generated_title(title: str, max_length: int = 40) -> str:
    """Clean and limit an LLM-generated conversation title."""
    cleaned = " ".join(title.strip().strip("\"'`").split())
    prefixes = (
        "title:",
        "conversation title:",
        "short title:",
    )
    lowered = cleaned.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    cleaned = cleaned.strip(" .,:;!?\"'`")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit(" ", 1)[0] or cleaned[:max_length]

    return cleaned or ""


def _fallback_title(question: str, max_length: int = 60) -> str:
    """Create a deterministic title when LLM title generation fails."""
    title = question.strip().replace("\n", " ")
    if len(title) > max_length:
        title = f"{title[: max_length - 3]}..."
    return title or "New Chat"


async def _store_stream_failure(
    session: AsyncSession,
    conversation_id: UUID,
    agent_run,
    error_message: str,
    started_at: float,
    code: ErrorCode,
) -> None:
    """Persist a failed streamed agent response."""
    await create_message(
        session,
        conversation_id=conversation_id,
        role=MessageRole.assistant,
        content=error_message,
        status=MessageStatus.failed,
    )
    await mark_agent_run_failed(
        session,
        agent_run,
        error_message=error_message,
        latency_ms=_elapsed_ms(started_at),
        status_code=str(int(code)),
    )
    await session.commit()


def _sse_response(events: AsyncGenerator[str, None]) -> StreamingResponse:
    """Wrap an async event generator as an SSE response."""
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _single_sse_event(event_type: str, payload: dict) -> AsyncGenerator[str, None]:
    """Yield one SSE event for early validation failures."""
    yield _format_sse(event_type, payload)


def _format_sse(event_type: str, payload: dict) -> str:
    """Format one payload as a server-sent event."""
    return (
        f"event: {event_type}\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    )


def _elapsed_ms(started_at: float) -> int:
    """Return elapsed milliseconds from a perf counter timestamp."""
    return int((perf_counter() - started_at) * 1000)


def _agent_error_code(exc: Exception) -> ErrorCode:
    """Map agent client exceptions to application error codes."""
    if isinstance(exc, ValueError):
        return ErrorCode.AGENT_SERVICE_BAD_RESPONSE
    return ErrorCode.AGENT_SERVICE_UNAVAILABLE


def _agent_http_status(exc: Exception) -> int:
    """Map agent client exceptions to HTTP status codes."""
    if isinstance(exc, ValueError):
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_503_SERVICE_UNAVAILABLE


def _list_or_empty(value: object) -> list[dict]:
    """Return list data when available, otherwise an empty list."""
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _dict_or_empty(value: object) -> dict:
    """Return dict data when available, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}

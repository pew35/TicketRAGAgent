"""Shared response, event, and error types for the TicketRAGAgent.

This module keeps agent-facing contracts in one place:
- ``AgentEvent`` is used by streaming code to report status, tokens, sources,
  errors, and completion events.
- ``AgentError`` is the standard exception raised by internal agent steps.
- ``AgentResponse`` is the final non-streaming response shape used by APIs,
  tests, and command-line callers.

Business code should raise ``AgentError`` with a precise ``AgentStatusCode``.
The outer agent workflow can then convert that exception into a stable error
event or response without leaking low-level implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

EventType = Literal["status", "token", "sources", "error", "done"]


class AgentStatusCode(str, Enum):
    """Stable status and error codes emitted by the RAG agent."""

    STARTED = "STARTED"
    VALIDATING_INPUT = "VALIDATING_INPUT"
    EMBEDDING_STARTED = "EMBEDDING_STARTED"
    EMBEDDING_COMPLETED = "EMBEDDING_COMPLETED"
    SEARCH_STARTED = "SEARCH_STARTED"
    SEARCH_COMPLETED = "SEARCH_COMPLETED"
    NO_RESULTS = "NO_RESULTS"
    CONTEXT_BUILD_STARTED = "CONTEXT_BUILD_STARTED"
    CONTEXT_BUILD_COMPLETED = "CONTEXT_BUILD_COMPLETED"
    GENERATION_STARTED = "GENERATION_STARTED"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"
    COMPLETED = "COMPLETED"

    INVALID_QUESTION = "INVALID_QUESTION"
    OLLAMA_EMBEDDING_FAILED = "OLLAMA_EMBEDDING_FAILED"
    WEAVIATE_CONNECTION_FAILED = "WEAVIATE_CONNECTION_FAILED"
    WEAVIATE_SEARCH_FAILED = "WEAVIATE_SEARCH_FAILED"
    CONTEXT_BUILD_FAILED = "CONTEXT_BUILD_FAILED"
    OLLAMA_GENERATION_FAILED = "OLLAMA_GENERATION_FAILED"
    OLLAMA_STREAM_FAILED = "OLLAMA_STREAM_FAILED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


ERROR_HTTP_STATUS_MAP: dict[AgentStatusCode, int] = {
    AgentStatusCode.INVALID_QUESTION: 400,
    AgentStatusCode.OLLAMA_EMBEDDING_FAILED: 502,
    AgentStatusCode.WEAVIATE_CONNECTION_FAILED: 503,
    AgentStatusCode.WEAVIATE_SEARCH_FAILED: 502,
    AgentStatusCode.CONTEXT_BUILD_FAILED: 500,
    AgentStatusCode.OLLAMA_GENERATION_FAILED: 502,
    AgentStatusCode.OLLAMA_STREAM_FAILED: 502,
    AgentStatusCode.UNKNOWN_ERROR: 500,
}


@dataclass(frozen=True)
class AgentEvent:
    """One streaming event produced while the agent is answering a question."""

    type: EventType
    code: AgentStatusCode
    content: str
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event into a JSON-friendly dictionary."""
        return {
            "type": self.type,
            "code": self.code.value,
            "content": self.content,
            "data": self.data,
        }


@dataclass(frozen=True)
class AgentResponse:
    """Final non-streaming response returned after the full RAG flow finishes."""

    success: bool
    code: AgentStatusCode
    message: str
    answer: str | None = None
    sources: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the response into a JSON-friendly dictionary."""
        return {
            "success": self.success,
            "code": self.code.value,
            "message": self.message,
            "answer": self.answer,
            "sources": self.sources,
            "metadata": self.metadata,
            "error": self.error,
        }


class AgentError(Exception):
    """Standard exception for expected failures inside the RAG agent."""

    def __init__(
        self,
        code: AgentStatusCode,
        message: str,
        *,
        stage: str,
        detail: str | None = None,
        cause: Exception | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage
        self.detail = detail
        self.cause = cause
        self.data = data or {}

    @property
    def http_status(self) -> int:
        """Return the default HTTP status for API layers that expose this error."""
        return ERROR_HTTP_STATUS_MAP.get(self.code, 500)

    def to_error_data(self) -> dict[str, Any]:
        """Return structured error details safe for logs and API responses."""
        error_data: dict[str, Any] = {
            "stage": self.stage,
            "error_type": type(self.cause).__name__ if self.cause else type(self).__name__,
            "http_status": self.http_status,
        }

        if self.detail:
            error_data["detail"] = self.detail

        if self.data:
            error_data["metadata"] = self.data

        return error_data

    def to_event(self) -> AgentEvent:
        """Convert this error into a streaming error event."""
        return AgentEvent(
            type="error",
            code=self.code,
            content=self.message,
            data=self.to_error_data(),
        )

    def to_response(self) -> AgentResponse:
        """Convert this error into a final non-streaming failure response."""
        return AgentResponse(
            success=False,
            code=self.code,
            message=self.message,
            error=self.to_error_data(),
        )


def status_event(
    code: AgentStatusCode,
    content: str,
    data: dict[str, Any] | None = None,
) -> AgentEvent:
    """Create a standard status event for visible agent progress."""
    return AgentEvent(type="status", code=code, content=content, data=data)


def token_event(token: str) -> AgentEvent:
    """Create a token event for streaming model output."""
    return AgentEvent(
        type="token",
        code=AgentStatusCode.GENERATION_STARTED,
        content=token,
    )


def sources_event(
    sources: list[dict[str, Any]],
    data: dict[str, Any] | None = None,
) -> AgentEvent:
    """Create a sources event containing retrieved ticket references."""
    event_data = {"sources": sources}
    if data:
        event_data.update(data)

    return AgentEvent(
        type="sources",
        code=AgentStatusCode.SEARCH_COMPLETED,
        content=f"Found {len(sources)} relevant ticket source(s).",
        data=event_data,
    )


def done_event(
    code: AgentStatusCode = AgentStatusCode.COMPLETED,
    content: str = "Answer generation completed.",
    data: dict[str, Any] | None = None,
) -> AgentEvent:
    """Create a terminal event for a completed agent run."""
    return AgentEvent(type="done", code=code, content=content, data=data)


def unknown_error_event(exc: Exception, *, stage: str = "unknown") -> AgentEvent:
    """Convert an unexpected exception into a stable streaming error event."""
    return AgentError(
        AgentStatusCode.UNKNOWN_ERROR,
        "An unexpected agent error occurred.",
        stage=stage,
        detail=str(exc),
        cause=exc,
    ).to_event()


def success_response(
    answer: str,
    *,
    sources: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    message: str = "success",
) -> AgentResponse:
    """Create the standard successful response for non-streaming RAG calls."""
    return AgentResponse(
        success=True,
        code=AgentStatusCode.COMPLETED,
        message=message,
        answer=answer,
        sources=sources,
        metadata=metadata,
    )


def error_response(error: AgentError) -> AgentResponse:
    """Create the standard failed response from an ``AgentError``."""
    return error.to_response()

"""HTTP test service for the TicketRAGAgent.

This module exposes a small FastAPI app for local development:
- ``GET /`` serves the browser test page.
- ``GET /health`` checks that the service is running.
- ``POST /api/ask`` returns one complete non-streaming response.
- ``POST /api/ask/stream`` streams agent events as newline-delimited JSON.

Run locally:

    uvicorn http_service:app --reload --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from typing import Iterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent.ticket_agent import TicketRAGAgent

BASE_DIR = Path(__file__).resolve().parent
WEB_INDEX = BASE_DIR / "web" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Create one reusable RAG agent for the HTTP service lifetime."""
    agent = TicketRAGAgent()
    app.state.agent = agent
    try:
        yield
    finally:
        agent.close()


app = FastAPI(title="TicketRAGAgent Test Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    """Request body for asking the ticket RAG agent a question."""

    question: str = Field(..., min_length=1)


class TitleRequest(BaseModel):
    """Request body for generating a conversation title."""

    question: str = Field(..., min_length=1)
    max_length: int = Field(default=40, ge=10, le=80)


@app.get("/")
def index() -> FileResponse:
    """Serve the local browser test page."""
    return FileResponse(WEB_INDEX)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a tiny health response for local checks."""
    return {"status": "ok"}


@app.post("/api/ask")
def ask(request: AskRequest, http_request: Request) -> dict:
    """Return a complete non-streaming agent response."""
    agent: TicketRAGAgent = http_request.app.state.agent
    return agent.answer(request.question).to_dict()


@app.post("/api/title")
def title(request: TitleRequest, http_request: Request) -> dict[str, str]:
    """Generate a short title for a conversation."""
    agent: TicketRAGAgent = http_request.app.state.agent
    return {"title": agent.generate_title(request.question, request.max_length)}


@app.post("/api/ask/stream")
def ask_stream(request: AskRequest, http_request: Request) -> StreamingResponse:
    """Stream agent events as newline-delimited JSON for the browser page."""

    def event_lines() -> Iterator[str]:
        agent: TicketRAGAgent = http_request.app.state.agent
        for event in agent.stream_answer(request.question):
            yield json.dumps(event.to_dict(), ensure_ascii=False) + "\n"

    return StreamingResponse(event_lines(), media_type="application/x-ndjson")

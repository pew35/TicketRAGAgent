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
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent.ticket_agent import TicketRAGAgent

BASE_DIR = Path(__file__).resolve().parent
WEB_INDEX = BASE_DIR / "web" / "index.html"

app = FastAPI(title="TicketRAGAgent Test Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    """Request body for asking the ticket RAG agent a question."""

    question: str = Field(..., min_length=1)


@app.get("/")
def index() -> FileResponse:
    """Serve the local browser test page."""
    return FileResponse(WEB_INDEX)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a tiny health response for local checks."""
    return {"status": "ok"}


@app.post("/api/ask")
def ask(request: AskRequest) -> dict:
    """Return a complete non-streaming agent response."""
    agent = TicketRAGAgent()
    try:
        return agent.answer(request.question).to_dict()
    finally:
        agent.close()


@app.post("/api/ask/stream")
def ask_stream(request: AskRequest) -> StreamingResponse:
    """Stream agent events as newline-delimited JSON for the browser page."""

    def event_lines() -> Iterator[str]:
        agent = TicketRAGAgent()
        try:
            for event in agent.stream_answer(request.question):
                yield json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
        finally:
            agent.close()

    return StreamingResponse(event_lines(), media_type="application/x-ndjson")

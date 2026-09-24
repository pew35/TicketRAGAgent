"""Main RAG agent for answering questions with historical service tickets.

The agent owns the runtime workflow:
1. validate the user question
2. embed the question with LangChain/Ollama
3. search similar ticket vectors in Weaviate
4. build a compact RAG context from retrieved tickets
5. stream the final answer from the chat model

The module exposes both streaming and non-streaming entry points. Streaming
callers receive ``AgentEvent`` objects for progress, source references, output
tokens, errors, and completion. Non-streaming callers receive one
``AgentResponse`` after the same workflow finishes.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any, Iterator
from urllib.parse import urlparse

import weaviate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from weaviate.classes.query import MetadataQuery

from agent.config import RAGConfig, config
from agent.import_data import TicketImportData
from agent.response import (
    AgentError,
    AgentEvent,
    AgentResponse,
    AgentStatusCode,
    done_event,
    sources_event,
    status_event,
    success_response,
    token_event,
    unknown_error_event,
)


# TicketSource: normalized search result used for prompts, API responses, and UI cards.
@dataclass(frozen=True)
class TicketSource:
    """A relevant historical ticket returned by vector search."""

    ticket_id: str
    issue_type: str
    priority: str
    description: str
    solution: str
    similarity: float

    def to_context_block(self, index: int) -> str:
        """Format customer-safe reference facts for the answer prompt."""
        return f"""
Reference {index}
Issue Type: {self.issue_type}
Customer Problem:
{self.description}
Past Resolution Example (possible guidance, not a promise for this customer):
{self.solution}
""".strip()

    def to_dict(self) -> dict[str, Any]:
        """Serialize this source into a JSON-friendly dictionary."""
        return {
            "ticket_id": self.ticket_id,
            "issue_type": self.issue_type,
            "priority": self.priority,
            "description": self.description,
            "solution": self.solution,
            "similarity": round(self.similarity, 4),
        }


# TicketRAGAgent: orchestrates embedding, retrieval, prompt construction, and generation.
class TicketRAGAgent:
    """RAG agent that answers support questions using historical ticket records."""

    def __init__(
        self,
        rag_config: RAGConfig = config,
        rebuild_database: bool = True,
    ) -> None:
        self.config = rag_config
        self.embeddings = OllamaEmbeddings(
            model=self.config.ollama.embed_model,
            base_url=self.config.ollama.host,
        )
        self.llm = ChatOllama(
            model=self.config.ollama.chat_model,
            base_url=self.config.ollama.host,
            temperature=0.1,
        )
        if rebuild_database:
            self._setup_database()

    def close(self) -> None:
        """Close network resources owned by the agent instance."""
        sync_client = getattr(self.llm, "_client", None)
        if sync_client and hasattr(sync_client, "close"):
            sync_client.close()

        embed_client = getattr(self.embeddings, "_client", None)
        if embed_client and hasattr(embed_client, "close"):
            embed_client.close()

    def _setup_database(self) -> None:
        """Rebuild the ticket vector database from CSV data during agent startup."""
        print("Initializing ticket vector database...")
        importer = TicketImportData(self.config.data_path)
        try:
            imported_count = importer.import_tickets()
            print(
                f"Stored {imported_count} ticket records in "
                f"{self.config.weaviate.collection_name}"
            )
        finally:
            importer.close()

    def stream_answer(self, question: str) -> Iterator[AgentEvent]:
        """Stream status, sources, answer tokens, errors, and completion events."""
        started_at = time.perf_counter()

        try:
            # Send the first visible state so callers know the agent started.
            yield status_event(
                AgentStatusCode.STARTED,
                "Thinking...",
                self._timing_data(started_at),
            )

            # Validate user input before calling external services.
            clean_question = self._validate_question(question)

            # Convert the question into an embedding vector for semantic search.
            stage_started_at = time.perf_counter()
            yield status_event(
                AgentStatusCode.EMBEDDING_STARTED,
                "Embedding question...",
                self._timing_data(
                    started_at,
                    model=self.config.ollama.embed_model,
                ),
            )
            query_vector = self._embed_question(clean_question)
            yield status_event(
                AgentStatusCode.EMBEDDING_COMPLETED,
                "Question embedding completed.",
                self._timing_data(started_at, stage_started_at),
            )

            # Search Weaviate for historical tickets closest to the question vector.
            stage_started_at = time.perf_counter()
            yield status_event(
                AgentStatusCode.SEARCH_STARTED,
                "Searching similar tickets...",
                self._timing_data(
                    started_at,
                    collection=self.config.weaviate.collection_name,
                    top_k=self.config.top_k,
                    similarity_threshold=self.config.similarity_threshold,
                ),
            )
            sources = self._search_tickets(query_vector)
            search_stage_ms = self._elapsed_ms(stage_started_at)

            # Treat "no matches" as a valid result, not a system failure.
            if not sources:
                message = (
                    "No sufficiently similar historical tickets were found. "
                    "Please add more ticket data or lower the similarity threshold."
                )
                yield status_event(
                    AgentStatusCode.NO_RESULTS,
                    message,
                    self._timing_data(
                        started_at,
                        stage_ms=search_stage_ms,
                        sources_count=0,
                    ),
                )
                yield done_event(
                    code=AgentStatusCode.NO_RESULTS,
                    content="No relevant ticket sources found.",
                    data=self._timing_data(started_at, sources_count=0),
                )
                return

            # Send structured source records so UI/API callers can show citations.
            source_dicts = [source.to_dict() for source in sources]
            yield sources_event(
                source_dicts,
                self._timing_data(
                    started_at,
                    stage_ms=search_stage_ms,
                    sources_count=len(sources),
                ),
            )

            # Build the RAG context that will be inserted into the prompt.
            stage_started_at = time.perf_counter()
            yield status_event(
                AgentStatusCode.CONTEXT_BUILD_STARTED,
                "Building answer context...",
                self._timing_data(started_at),
            )
            context = self._build_context(sources)
            yield status_event(
                AgentStatusCode.CONTEXT_BUILD_COMPLETED,
                "Answer context completed.",
                self._timing_data(started_at, stage_started_at),
            )

            # Stream the final model answer and wrap each text piece as token events.
            stage_started_at = time.perf_counter()
            yield status_event(
                AgentStatusCode.GENERATION_STARTED,
                "Generating answer...",
                self._timing_data(
                    started_at,
                    model=self.config.ollama.chat_model,
                    temperature=0.1,
                ),
            )
            for token in self._stream_llm_answer(clean_question, context):
                yield token_event(token)

            yield status_event(
                AgentStatusCode.GENERATION_COMPLETED,
                "Answer generation completed.",
                self._timing_data(started_at, stage_started_at),
            )
            yield done_event(
                data=self._timing_data(started_at, sources_count=len(sources))
            )
        except AgentError as exc:
            # Convert expected agent failures into standard error and done events.
            error_event = exc.to_event()
            yield AgentEvent(
                type=error_event.type,
                code=error_event.code,
                content=error_event.content,
                data={
                    **(error_event.data or {}),
                    **self._timing_data(started_at),
                },
            )
            yield done_event(
                code=exc.code,
                content="Agent run failed.",
                data=self._timing_data(started_at, stage=exc.stage),
            )
        except Exception as exc:
            # Catch unexpected bugs so stream callers still receive a stable error.
            error_event = unknown_error_event(exc, stage="ticket_agent")
            yield AgentEvent(
                type=error_event.type,
                code=error_event.code,
                content=error_event.content,
                data={
                    **(error_event.data or {}),
                    **self._timing_data(started_at),
                },
            )
            yield done_event(
                code=AgentStatusCode.UNKNOWN_ERROR,
                content="Agent run failed.",
                data=self._timing_data(started_at, stage="ticket_agent"),
            )

    def answer(self, question: str) -> AgentResponse:
        """Run the full RAG workflow and return one final response object."""
        answer_parts: list[str] = []
        sources: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {"events": []}
        no_results = False

        for event in self.stream_answer(question):
            metadata["events"].append(event.to_dict())

            if event.type == "token":
                answer_parts.append(event.content)
            elif event.type == "sources" and event.data:
                sources = list(event.data.get("sources", []))
            elif event.type == "status" and event.code == AgentStatusCode.NO_RESULTS:
                no_results = True
            elif event.type == "error":
                return AgentResponse(
                    success=False,
                    code=event.code,
                    message=event.content,
                    sources=sources or None,
                    metadata=metadata,
                    error=event.data,
                )

        if no_results:
            return AgentResponse(
                success=True,
                code=AgentStatusCode.NO_RESULTS,
                message="No relevant ticket sources found.",
                answer=(
                    "No sufficiently similar historical tickets were found, "
                    "so I cannot provide a ticket-grounded answer."
                ),
                sources=[],
                metadata=metadata,
            )

        return success_response(
            "".join(answer_parts).strip(),
            sources=sources,
            metadata=metadata,
        )

    def generate_title(self, question: str, max_length: int = 40) -> str:
        """Generate a short conversation title from the user's first question."""
        clean_question = self._validate_question(question)
        prompt = f"""
Create a short English title for this customer support conversation.

Rules:
- Return only the title text.
- Use 3 to 6 words.
- Maximum {max_length} characters.
- No quotes, punctuation, prefixes, explanations, or full sentence.
- Focus on the product issue and requested action.

Customer question: {clean_question}
""".strip()
        messages = [
            {
                "role": "system",
                "content": (
                    "You write compact conversation titles. Return only the "
                    "title and nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.llm.invoke(messages)
        except Exception as exc:
            raise AgentError(
                AgentStatusCode.OLLAMA_STREAM_FAILED,
                "Failed to generate conversation title.",
                stage="title_generation",
                detail=str(exc),
                cause=exc,
                data={"model": self.config.ollama.chat_model},
            ) from exc

        return self._clean_title(self._extract_chat_content(response), max_length)

    def _clean_title(self, title: str, max_length: int) -> str:
        """Normalize and trim a model-generated conversation title."""
        cleaned = " ".join(title.strip().strip("\"'`").split())
        lowered = cleaned.lower()
        for prefix in ("title:", "conversation title:", "short title:"):
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
                break

        cleaned = cleaned.split("\n", 1)[0].strip(" .,:;!?\"'`")
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rsplit(" ", 1)[0] or cleaned[:max_length]

        return cleaned

    def _validate_question(self, question: str) -> str:
        """Validate and normalize the user question before external calls."""
        if not isinstance(question, str):
            raise AgentError(
                AgentStatusCode.INVALID_QUESTION,
                "Question must be a string.",
                stage="validation",
                detail=f"Received type: {type(question).__name__}",
            )

        clean_question = question.strip()
        if not clean_question:
            raise AgentError(
                AgentStatusCode.INVALID_QUESTION,
                "Question cannot be empty.",
                stage="validation",
            )

        return clean_question

    def _elapsed_ms(self, started_at: float) -> int:
        """Return elapsed milliseconds since the given monotonic timestamp."""
        return round((time.perf_counter() - started_at) * 1000)

    def _timing_data(
        self,
        started_at: float,
        stage_started_at: float | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build common timing metadata for status, source, error, and done events."""
        data: dict[str, Any] = {"elapsed_ms": self._elapsed_ms(started_at)}

        if stage_started_at is not None:
            data["stage_ms"] = self._elapsed_ms(stage_started_at)

        data.update(extra)
        return data

    def _embed_question(self, question: str) -> list[float]:
        """Generate a vector embedding for the user question with LangChain."""
        try:
            vector = self.embeddings.embed_query(question)
            if not vector:
                raise RuntimeError("Ollama returned no embedding vectors")
            return list(vector)
        except Exception as exc:
            raise AgentError(
                AgentStatusCode.OLLAMA_EMBEDDING_FAILED,
                "Failed to generate question embedding.",
                stage="embedding",
                detail=str(exc),
                cause=exc,
                data={"model": self.config.ollama.embed_model},
            ) from exc

    def _search_tickets(self, query_vector: list[float]) -> list[TicketSource]:
        """Search Weaviate for tickets similar to the question vector."""
        client = self._connect_weaviate()
        try:
            collection = client.collections.get(self.config.weaviate.collection_name)
            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=self.config.top_k,
                return_metadata=MetadataQuery(distance=True),
                return_properties=[
                    "ticket_id",
                    "issue_type",
                    "description",
                    "solution",
                    "priority",
                ],
            )
            return self._parse_search_results(response.objects)
        except AgentError:
            raise
        except Exception as exc:
            raise AgentError(
                AgentStatusCode.WEAVIATE_SEARCH_FAILED,
                "Failed to search similar tickets.",
                stage="search",
                detail=str(exc),
                cause=exc,
                data={"collection": self.config.weaviate.collection_name},
            ) from exc
        finally:
            client.close()

    def _connect_weaviate(self) -> weaviate.WeaviateClient:
        """Create a Weaviate client from the configured HTTP and gRPC ports."""
        parsed = urlparse(self.config.weaviate.host)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080

        try:
            return weaviate.connect_to_local(
                host=host,
                port=port,
                grpc_port=self.config.weaviate.grpc_port,
            )
        except Exception as exc:
            raise AgentError(
                AgentStatusCode.WEAVIATE_CONNECTION_FAILED,
                "Failed to connect to Weaviate.",
                stage="search",
                detail=str(exc),
                cause=exc,
                data={
                    "host": self.config.weaviate.host,
                    "grpc_port": self.config.weaviate.grpc_port,
                },
            ) from exc

    def _parse_search_results(self, objects: list[Any]) -> list[TicketSource]:
        """Normalize Weaviate objects and filter by configured similarity."""
        sources: list[TicketSource] = []

        for item in objects:
            properties = item.properties or {}
            distance = getattr(item.metadata, "distance", None)
            similarity = self._distance_to_similarity(distance)

            if similarity < self.config.similarity_threshold:
                continue

            sources.append(
                TicketSource(
                    ticket_id=str(properties.get("ticket_id", "")),
                    issue_type=str(properties.get("issue_type", "")),
                    priority=str(properties.get("priority", "")),
                    description=str(properties.get("description", "")),
                    solution=str(properties.get("solution", "")),
                    similarity=similarity,
                )
            )

        return sources

    def _distance_to_similarity(self, distance: float | None) -> float:
        """Convert Weaviate vector distance into a simple similarity score."""
        if distance is None:
            return 0.0

        similarity = 1.0 - float(distance)
        return max(0.0, min(1.0, similarity))

    def _build_context(self, sources: list[TicketSource]) -> str:
        """Build compact prompt context from retrieved ticket sources."""
        try:
            return "\n\n---\n\n".join(
                source.to_context_block(index)
                for index, source in enumerate(sources, start=1)
            )
        except Exception as exc:
            raise AgentError(
                AgentStatusCode.CONTEXT_BUILD_FAILED,
                "Failed to build RAG context.",
                stage="context_building",
                detail=str(exc),
                cause=exc,
            ) from exc

    def _stream_llm_answer(self, question: str, context: str) -> Iterator[str]:
        """Stream the final answer from LangChain and yield one character at a time."""
        # Fill the QA prompt with retrieved ticket context and the user question.
        prompt = self.config.prompts.qa_prompt_template.format(
            context=context,
            question=question,
        )

        # Send system instructions separately from the user prompt.
        messages = [
            {"role": "system", "content": self.config.prompts.system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            # LangChain returns streaming chunks from the chat model.
            for chunk in self.llm.stream(messages):
                content = self._extract_chat_content(chunk)

                # Split chunks into characters so the UI can render a typing effect.
                for character in content:
                    yield character
        except Exception as exc:
            # Normalize LangChain/Ollama generation failures into agent errors.
            raise AgentError(
                AgentStatusCode.OLLAMA_STREAM_FAILED,
                "Failed while streaming answer from LangChain/Ollama.",
                stage="generation",
                detail=str(exc),
                cause=exc,
                data={"model": self.config.ollama.chat_model},
            ) from exc

    def _extract_chat_content(self, chunk: Any) -> str:
        """Read assistant text from LangChain, dict-style, or object-style chunks."""
        if isinstance(chunk, dict):
            message = chunk.get("message", {})
            return str(message.get("content", ""))

        content = getattr(chunk, "content", None)
        if content is not None:
            return str(content)

        message = getattr(chunk, "message", None)
        if isinstance(message, dict):
            return str(message.get("content", ""))

        return str(getattr(message, "content", "") or "")

def main() -> None:
    """Run a small command-line streaming demo for local development."""
    parser = argparse.ArgumentParser(description="Ask the TicketRAGAgent a question.")
    parser.add_argument("question", nargs="+", help="Support question to answer")
    args = parser.parse_args()

    agent = TicketRAGAgent()
    question = " ".join(args.question)

    for event in agent.stream_answer(question):
        timing = ""
        if event.data:
            elapsed_ms = event.data.get("elapsed_ms")
            stage_ms = event.data.get("stage_ms")
            if elapsed_ms is not None:
                timing = f" elapsed={elapsed_ms}ms"
            if stage_ms is not None:
                timing += f" stage={stage_ms}ms"

        if event.type == "status":
            print(f"\n[{int(event.code)}] {event.content}{timing}")
        elif event.type == "sources":
            print(f"\n[{int(event.code)}] {event.content}{timing}")
        elif event.type == "token":
            print(event.content, end="", flush=True)
        elif event.type == "error":
            print(f"\n[{int(event.code)}] {event.content}{timing}")
            if event.data:
                print(event.data)
        elif event.type == "done":
            print(f"\n[{int(event.code)}] {event.content}{timing}")


if __name__ == "__main__":
    main()

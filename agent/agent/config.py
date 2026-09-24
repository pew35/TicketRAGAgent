"""Central configuration for the TicketRAGAgent RAG pipeline.

This module defines all runtime settings in one place so the rest of the
application can stay decoupled from hard-coded values. Settings are grouped
into small, immutable dataclasses (Ollama, Weaviate, prompts, and retrieval
parameters) and assembled into a single ``RAGConfig`` object.

Typical usage::

    from agent.config import config

    config.ollama.chat_model
    config.weaviate.host
    config.prompts.qa_prompt_template.format(context=..., question=...)
    config.top_k

Environment variables (all optional) override defaults at startup:

    OLLAMA_HOST, EMBED_MODEL, CHAT_MODEL
    WEAVIATE_HOST, WEAVIATE_GRPC_PORT, WEAVIATE_COLLECTION
    DATA_PATH, TOP_K, SIMILARITY_THRESHOLD
    SYSTEM_PROMPT, QA_PROMPT_TEMPLATE

The module exposes ``config = load_config()`` so importers get a ready-to-use
singleton without calling ``load_config()`` themselves.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_SYSTEM_PROMPT = """
You are the customer-facing support assistant for an online shopping application.
Reply directly to the customer. Historical tickets are private evidence that
may inform the answer, never content to describe or quote.

Response requirements:
1. Always answer in English and address the customer as "you".
2. The customer's product, problem, and timing are authoritative. Never replace them with details from another ticket.
3. Apply only the resolution that is directly relevant to the question. Ignore unrelated retrieved cases.
4. Do not mention ticket IDs, historical records, retrieval, similarity scores, or internal workflows.
5. Do not invent policies, interface labels, fees, timelines, or actions not supported by the reference material.
6. Do not claim that you already checked an account, sent something, issued a refund, or completed an action.
7. Convert a past staff action into the next step the customer can take or a possible outcome they can request.
8. If account-specific verification is required, say what needs to be checked without pretending it has been checked.
9. Keep the response to two to four concise sentences with a calm, natural tone.
""".strip()

DEFAULT_QA_PROMPT_TEMPLATE = """
Use the private reference material below to answer the customer's question.
Do not reveal or describe the reference material in your response.

Private reference material:
{context}

Customer question: {question}

Write the final message exactly as it should be shown to the customer.
Use only the relevant resolution from the reference material.
Answer directly in two to four concise English sentences.
Preserve every fact stated by the customer.
Do not expose internal information or claim an action has already been completed.
""".strip()


# Ollama: local LLM server for embeddings (vector search) and chat (answer generation).
@dataclass(frozen=True)
class OllamaConfig:
    host: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    chat_model: str = "llama3.1:8b"


# Weaviate: vector database that stores ticket embeddings and serves similarity search.
@dataclass(frozen=True)
class WeaviateConfig:
    host: str = "http://localhost:8080"
    grpc_port: int = 50051
    collection_name: str = "ServiceTicket"


# Prompts: system role + user QA template passed to the chat model during RAG.
@dataclass(frozen=True)
class PromptConfig:
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    qa_prompt_template: str = DEFAULT_QA_PROMPT_TEMPLATE


# RAGConfig: top-level bundle consumed by import, retrieval, and generation modules.
@dataclass(frozen=True)
class RAGConfig:
    ollama: OllamaConfig
    weaviate: WeaviateConfig
    prompts: PromptConfig
    data_path: Path
    top_k: int = 5
    similarity_threshold: float = 0.3


def load_config() -> RAGConfig:
    """Build and return the full RAG configuration from defaults and env vars.

    Reads optional environment variables and falls back to built-in defaults
    when a variable is not set. Paths are resolved relative to the ``agent/``
    package root (parent of this ``agent`` subpackage).

    Returns:
        RAGConfig: Immutable snapshot of Ollama, Weaviate, prompt, data, and
        retrieval settings used by import, search, and generation code.
    """
    data_path = Path(
        os.getenv("DATA_PATH", str(AGENT_DIR / "data" / "service_tickets.csv"))
    )

    ollama = OllamaConfig(
        host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        embed_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
        chat_model=os.getenv("CHAT_MODEL", "llama3.1:8b"),
    )

    weaviate = WeaviateConfig(
        host=os.getenv("WEAVIATE_HOST", "http://localhost:8080"),
        grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
        collection_name=os.getenv("WEAVIATE_COLLECTION", "ServiceTicket"),
    )

    prompts = PromptConfig(
        system_prompt=os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        qa_prompt_template=os.getenv("QA_PROMPT_TEMPLATE", DEFAULT_QA_PROMPT_TEMPLATE),
    )

    return RAGConfig(
        ollama=ollama,
        weaviate=weaviate,
        prompts=prompts,
        data_path=data_path,
        top_k=int(os.getenv("TOP_K", "5")),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.3")),
    )


# Singleton loaded once at import time; other modules should import `config` directly.
config = load_config()


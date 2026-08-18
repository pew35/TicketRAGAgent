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
You are a customer support knowledge base assistant. Use historical service ticket records to help support agents find solutions quickly.

Response requirements:
1. Always answer in English, regardless of the language used in the question
2. Start with the direct recommended action; do not begin with "Based on historical records" or similar meta commentary
3. Base your answer on directly relevant historical tickets; do not invent policies, facts, or ticket references
4. Provide concrete handling steps, decision criteria, and customer-facing recommendations
5. Mention ticket IDs only when they are directly relevant, preferably near the end
6. You are advising a support agent. Do not tell the customer to contact customer service; tell the support agent what action to take
7. Keep responses professional, clear, and actionable
""".strip()

DEFAULT_QA_PROMPT_TEMPLATE = """
Based on the following historical customer support ticket records, answer the support agent's question:

Historical ticket records:
{context}

Support agent question: {question}

Provide a concise, natural answer for a support agent.
Always answer in English.
Do not use a fixed template unless it makes the answer clearer.
Do not expose retrieval mechanics.
Mention only directly relevant ticket IDs, preferably near the end.
""".strip()


# Ollama: local LLM server for embeddings (vector search) and chat (answer generation).
@dataclass(frozen=True)
class OllamaConfig:
    host: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    chat_model: str = "llama3.2:latest"  # or llama3.1:8b


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
        chat_model=os.getenv("CHAT_MODEL", "llama3.2:latest"),
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


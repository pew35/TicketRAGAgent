"""Cloud-friendly RAG agent used by the public demo deployment."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from ..settings import Settings


SYSTEM_PROMPT = """
You are the customer-facing support assistant for an online shopping application.
Use the private historical ticket examples only as supporting evidence. Never
mention ticket IDs, retrieval, similarity scores, or internal records. Do not
claim that you already checked an account or completed an action. Answer in the
same language as the customer's question, address the customer directly, and
keep the response to two to four concise sentences.
""".strip()

TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]")


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    issue_type: str
    priority: str
    description: str
    solution: str

    def source(self, similarity: float) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "issue_type": self.issue_type,
            "priority": self.priority,
            "description": self.description,
            "solution": self.solution,
            "similarity": round(similarity, 4),
        }


class CloudTicketAgent:
    """Small in-process RAG implementation with an OpenAI-compatible LLM API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tickets = self._load_tickets(settings.ticket_data_path)
        self._idf, self._document_vectors = self._build_index(self.tickets)

    @property
    def ready(self) -> bool:
        return bool(self.tickets)

    async def answer(self, question: str) -> dict[str, Any]:
        answer_parts: list[str] = []
        sources: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {}
        async for event in self.stream_answer(question):
            if event["type"] == "token":
                answer_parts.append(str(event["content"]))
            elif event["type"] == "sources":
                sources = list((event.get("data") or {}).get("sources", []))
            elif event["type"] == "done":
                metadata = dict(event.get("data") or {})
        return {
            "code": 0,
            "answer": "".join(answer_parts).strip(),
            "sources": sources,
            "metadata": metadata,
        }

    async def stream_answer(self, question: str) -> AsyncGenerator[dict[str, Any], None]:
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Question cannot be empty.")

        started_at = perf_counter()
        yield self._event("status", "Searching support knowledge...")
        sources = self.search(clean_question)
        yield self._event(
            "sources",
            f"Found {len(sources)} relevant ticket source(s).",
            {"sources": sources},
        )
        yield self._event("status", "Generating answer...")

        answer_started_at = perf_counter()
        used_fallback = False
        try:
            async for token in self._stream_completion(clean_question, sources):
                yield self._event("token", token)
        except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError):
            used_fallback = True
            for token in self._fallback_answer(sources):
                yield self._event("token", token)

        yield self._event(
            "done",
            "Answer generation completed.",
            {
                "elapsed_ms": self._elapsed_ms(started_at),
                "generation_ms": self._elapsed_ms(answer_started_at),
                "sources_count": len(sources),
                "model": self.settings.llm_model,
                "fallback": used_fallback,
            },
        )

    async def generate_title(self, question: str, max_length: int = 40) -> str:
        prompt = (
            "Create a 3 to 6 word English title for this customer support "
            f"question. Return only the title, maximum {max_length} characters: "
            f"{question.strip()}"
        )
        try:
            title = await self._completion(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=24,
            )
        except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError):
            title = question

        cleaned = " ".join(title.strip().strip("\"'`").split())
        cleaned = cleaned.splitlines()[0].strip(" .,:;!?\"'`")
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rsplit(" ", 1)[0] or cleaned[:max_length]
        return cleaned or "New Chat"

    def search(self, question: str, limit: int = 5) -> list[dict[str, Any]]:
        query_vector = self._vectorize(self._tokens(question), self._idf)
        scored: list[tuple[float, Ticket]] = []
        for ticket, document_vector in zip(self.tickets, self._document_vectors):
            score = self._cosine(query_vector, document_vector)
            if score > 0:
                scored.append((score, ticket))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [ticket.source(score) for score, ticket in scored[:limit]]

    async def _stream_completion(
        self,
        question: str,
        sources: list[dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        if not self.settings.llm_api_key:
            raise ValueError("SERVER_LLM_API_KEY is not configured.")

        context = "\n\n".join(
            (
                f"Issue type: {source['issue_type']}\n"
                f"Customer problem: {source['description']}\n"
                f"Past resolution example: {source['solution']}"
            )
            for source in sources
        ) or "No matching historical ticket was found."
        prompt = (
            "Use the private reference material below to answer the customer's "
            "question. Apply only relevant guidance and preserve the customer's "
            f"facts.\n\nPrivate reference material:\n{context}\n\n"
            f"Customer question: {question}"
        )
        payload = self._payload(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            temperature=0.1,
            max_tokens=300,
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            received_content = False
            async with client.stream(
                "POST",
                self.settings.llm_api_url,
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    event = json.loads(data)
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    content = (choices[0].get("delta") or {}).get("content")
                    if content:
                        received_content = True
                        yield str(content)
            if not received_content:
                raise ValueError("The language model returned an empty response.")

    async def _completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not self.settings.llm_api_key:
            raise ValueError("SERVER_LLM_API_KEY is not configured.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.settings.llm_api_url,
                headers=self._headers(),
                json=self._payload(
                    messages,
                    stream=False,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )
            response.raise_for_status()
            data = response.json()
        return str(data["choices"][0]["message"]["content"])

    def _payload(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        return {
            "model": self.settings.llm_model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
            "X-Title": self.settings.llm_site_name,
        }
        if self.settings.llm_site_url:
            headers["HTTP-Referer"] = self.settings.llm_site_url
        return headers

    def _fallback_answer(self, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return (
                "I could not find a closely related support case. Please contact "
                "customer support with your order details so the issue can be reviewed."
            )
        solution = str(sources[0]["solution"]).strip().rstrip(".")
        return (
            f"A similar issue was resolved with this approach: {solution}. "
            "Please contact support to confirm the appropriate action for your order."
        )

    @staticmethod
    def _load_tickets(path: Path) -> list[Ticket]:
        resolved_path = path if path.is_absolute() else Path.cwd() / path
        with resolved_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            rows = csv.DictReader(csv_file)
            return [
                Ticket(
                    ticket_id=row["ticket_id"].strip(),
                    issue_type=row["issue_type"].strip(),
                    priority=row["priority"].strip(),
                    description=row["description"].strip(),
                    solution=row["solution"].strip(),
                )
                for row in rows
                if row.get("ticket_id") and row.get("description") and row.get("solution")
            ]

    @classmethod
    def _build_index(
        cls,
        tickets: list[Ticket],
    ) -> tuple[dict[str, float], list[dict[str, float]]]:
        documents = [
            cls._tokens(
                f"{ticket.issue_type} {ticket.issue_type} "
                f"{ticket.description} {ticket.solution}"
            )
            for ticket in tickets
        ]
        document_frequency = Counter(
            token for document in documents for token in set(document)
        )
        count = max(len(documents), 1)
        idf = {
            token: math.log((count + 1) / (frequency + 1)) + 1
            for token, frequency in document_frequency.items()
        }
        return idf, [cls._vectorize(document, idf) for document in documents]

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return TOKEN_PATTERN.findall(text.lower())

    @staticmethod
    def _vectorize(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
        counts = Counter(token for token in tokens if token in idf)
        if not counts:
            return {}
        maximum = max(counts.values())
        return {
            token: (frequency / maximum) * idf[token]
            for token, frequency in counts.items()
        }

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        dot = sum(value * right.get(token, 0.0) for token, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)

    @staticmethod
    def _event(
        event_type: str,
        content: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {"type": event_type, "code": 0, "content": content, "data": data}

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

"""Terminal smoke test for the TicketRAGAgent.

Run this file to see the full RAG process in the terminal:

    python test_agent.py "How do I fix a password reset issue?"

The output prints each status event, retrieved source event, streamed answer
tokens, errors, and the final done event.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from agent.ticket_agent import TicketRAGAgent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def print_event(event_dict: dict[str, Any]) -> str:
    """Print one agent event in a readable terminal format."""
    event_type = event_dict["type"]
    code = event_dict["code"]
    content = event_dict["content"]
    data = event_dict.get("data")

    if event_type == "token":
        print(content, end="", flush=True)
        return content

    timing = ""
    if data:
        elapsed_ms = data.get("elapsed_ms")
        stage_ms = data.get("stage_ms")
        if elapsed_ms is not None:
            timing = f" elapsed={elapsed_ms}ms"
        if stage_ms is not None:
            timing += f" stage={stage_ms}ms"

    print()
    print(f"[{code}] {content}{timing}")

    if event_type in {"sources", "error"} and data:
        print(json.dumps(data, ensure_ascii=False, indent=2))

    return ""


def print_model_return(answer_parts: list[str]) -> None:
    """Print the exact final model text reconstructed from streamed tokens."""
    answer = "".join(answer_parts)

    print()
    print("=" * 80)
    print("MODEL_RETURN_TEXT")
    print("=" * 80)
    print(answer)

    print()
    print("=" * 80)
    print("MODEL_RETURN_JSON_STRING")
    print("=" * 80)
    print(json.dumps(answer, ensure_ascii=False))


def main() -> None:
    """Run the agent against one question and print the streaming event flow."""
    parser = argparse.ArgumentParser(description="Run a terminal TicketRAGAgent test.")
    parser.add_argument(
        "question",
        nargs="*",
        help="Question to ask. A default support question is used when omitted.",
    )
    args = parser.parse_args()

    question = " ".join(args.question).strip()
    if not question:
        question = "How should I handle a customer who cannot reset their password?"

    print("TicketRAGAgent terminal test")
    print(f"Question: {question}")

    agent = TicketRAGAgent()
    answer_parts: list[str] = []
    try:
        for event in agent.stream_answer(question):
            event_dict = event.to_dict()
            token = print_event(event_dict)
            if event_dict["type"] == "token":
                answer_parts.append(token)
    finally:
        agent.close()

    if answer_parts:
        print_model_return(answer_parts)


if __name__ == "__main__":
    main()

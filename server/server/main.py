"""ASGI entry point for running the Ticket RAG server with Uvicorn."""

from .web.app import create_app


app = create_app()

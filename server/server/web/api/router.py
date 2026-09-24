"""Top-level API router that collects all feature routers."""

from fastapi import APIRouter

from .conversations.router import router as conversations_router
from .docs.router import router as docs_router
from .monitoring.router import router as monitoring_router
from .users.router import router as users_router


api_router = APIRouter(prefix="/api")

api_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(
    conversations_router,
    prefix="/conversations",
    tags=["conversations"],
)
api_router.include_router(docs_router, prefix="/docs", tags=["docs"])


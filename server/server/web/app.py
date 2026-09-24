"""FastAPI application factory for the Ticket RAG server."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, UJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..logging import configure_logging
from ..settings import Settings, get_settings
from .api.response import (
    ApiResponse,
    http_exception_handler,
    success_response,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .api.router import api_router
from .app_events import create_lifespan


APP_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = APP_ROOT / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    active_settings = settings or get_settings()
    configure_logging(active_settings)

    app = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        debug=active_settings.debug,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        default_response_class=UJSONResponse,
        lifespan=create_lifespan(active_settings),
    )

    _setup_exception_handlers(app)
    _setup_middleware(app, active_settings)
    _setup_routes(app, active_settings)
    _setup_static(app)
    _setup_frontend(app, active_settings)

    return app


def _setup_exception_handlers(app: FastAPI) -> None:
    """Register handlers that keep API errors in the shared response format."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def _setup_middleware(app: FastAPI, settings: Settings) -> None:
    """Register HTTP middleware such as browser CORS support."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


def _setup_routes(app: FastAPI, settings: Settings) -> None:
    """Register application routes and API routers."""
    app.include_router(api_router)

    @app.get("/health", response_model=ApiResponse[dict[str, str]])
    async def health_check() -> ApiResponse[dict[str, str]]:
        """Return a simple service health response."""
        return success_response({"status": "ok", "service": settings.app_name})


def _setup_static(app: FastAPI) -> None:
    """Mount static files used by local API documentation pages."""
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _setup_frontend(app: FastAPI, settings: Settings) -> None:
    """Serve the production Vite build and provide SPA route fallback."""
    dist_dir = settings.frontend_dist_dir
    index_file = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"
    if not index_file.exists():
        return

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def frontend_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{frontend_path:path}", include_in_schema=False)
    async def frontend_fallback(frontend_path: str) -> FileResponse:
        if frontend_path == "api" or frontend_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found.")
        requested_file = (dist_dir / frontend_path).resolve()
        if dist_dir.resolve() in requested_file.parents and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(index_file)


def get_app() -> FastAPI:
    """Compatibility wrapper matching common FastAPI factory naming."""
    return create_app()

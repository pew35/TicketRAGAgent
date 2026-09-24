"""Documentation routes for OpenAPI browser UIs."""

from fastapi import APIRouter, Request
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse


router = APIRouter(include_in_schema=False)


@router.get("/swagger", response_class=HTMLResponse)
async def swagger_ui_html(request: Request) -> HTMLResponse:
    """Return the Swagger UI page for this API."""
    title = request.app.title
    return get_swagger_ui_html(
        openapi_url=request.app.openapi_url,
        title=f"{title} - Swagger UI",
        oauth2_redirect_url="/api/docs/swagger-redirect",
        swagger_js_url="/static/docs/swagger-ui-bundle.js",
        swagger_css_url="/static/docs/swagger-ui.css",
    )


@router.get("/swagger-redirect", response_class=HTMLResponse)
async def swagger_ui_redirect() -> HTMLResponse:
    """Return the Swagger OAuth2 redirect helper page."""
    return get_swagger_ui_oauth2_redirect_html()


@router.get("/redoc", response_class=HTMLResponse)
async def redoc_html(request: Request) -> HTMLResponse:
    """Return the ReDoc page for this API."""
    title = request.app.title
    return get_redoc_html(
        openapi_url=request.app.openapi_url,
        title=f"{title} - ReDoc",
        redoc_js_url="/static/docs/redoc.standalone.js",
    )

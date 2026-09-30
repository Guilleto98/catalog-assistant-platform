"""Application composition: dependencies, middleware, error mapping and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from fastapi.routing import APIRoute

from ..clients import CatalogApiError
from ..config import Settings, get_settings
from ..domain.errors import IntakeError
from ..domain.models import Attachment
from ..repositories import AttachmentRepository, DraftRepository, initialize_database
from ..services import (
    AttachmentService,
    DocumentExtractionService,
    DraftService,
    OpenAIStructuredExtractor,
    OpenAITranscriptionService,
    PdfParser,
    SpreadsheetParser,
)
from ..storage import AttachmentStorage
from ..platform import routes as platform_routes
from ..platform import contracts as public
from .intake_service import IntakeApplicationService
from .routes import router as intake_router

logger = logging.getLogger(__name__)
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
LEGACY_PATH_PREFIXES = ("/attachments", "/drafts")
V1_PATH_PREFIXES = ("/auth", "/conversations", "/admin", "/saved-filters")
SECURITY_RESPONSE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}
UNEXPECTED_ERROR = {
    "code": "INTERNAL_ERROR",
    "message": "No se pudo completar la operación.",
}


class Container:
    """Wires intake domain services and their persistence dependencies."""

    def __init__(self, settings: Settings) -> None:
        initialize_database(settings.intake_database_path)
        self.storage = AttachmentStorage(settings.attachment_storage_path)
        self.attachments = AttachmentService(
            self.storage,
            AttachmentRepository(settings.intake_database_path),
            settings.attachment_max_size_bytes,
            settings.attachment_allowed_extensions,
            settings.attachment_allowed_mime_types,
        )
        self.drafts = DraftService(DraftRepository(settings.intake_database_path))
        self.transcriber = OpenAITranscriptionService(settings.transcription_model)
        self.pdf = PdfParser(settings.pdf_max_characters)
        self.spreadsheet = SpreadsheetParser(settings.spreadsheet_max_cells)
        self.extraction = DocumentExtractionService(
            OpenAIStructuredExtractor(settings.document_extraction_model)
        )


def create_app(settings: Settings | None = None, container: Container | None = None, runtime=None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from ..platform.service import Platform

        app.state.container = container or Container(resolved_settings)
        app.state.intake_service = IntakeApplicationService(app.state.container)
        app.state.platform = Platform(resolved_settings, app.state.container, runtime=runtime)
        try:
            yield
        finally:
            await app.state.platform.close()

    app = FastAPI(title="Catalog Assistant Application API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-Id"],
        expose_headers=["X-Request-Id"],
    )
    _register_error_handlers(app)
    _register_middleware(app, resolved_settings)
    _register_routes(app, resolved_settings)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, _error: RequestValidationError):
        code = "INVALID_MESSAGE" if request.url.path.endswith("/messages") else "VALIDATION_ERROR"
        return _error_response(request, 422, code, "Los datos enviados no son válidos.")

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, error: HTTPException):
        code = "NOT_FOUND" if error.status_code == 404 else "HTTP_ERROR"
        return _error_response(request, error.status_code, code, "Recurso no disponible.")

    @app.exception_handler(IntakeError)
    async def intake_error_handler(request: Request, error: IntakeError):
        return _error_response(request, error.status_code, error.code, error.message)

    @app.exception_handler(CatalogApiError)
    async def catalog_error_handler(request: Request, _error: CatalogApiError):
        return _error_response(request, 503, "CATALOG_UNAVAILABLE", "El catálogo no está disponible.")

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, error: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error("application_error request_id=%s error_type=%s", request_id, type(error).__name__)
        return _error_response(request, 500, **UNEXPECTED_ERROR)


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "requestId": request_id}},
        headers={"X-Request-Id": request_id},
    )


def _register_middleware(app: FastAPI, settings: Settings) -> None:
    @app.middleware("http")
    async def request_boundary(request: Request, call_next):
        started = time.perf_counter()
        request.state.request_id = _request_id(request.headers.get("X-Request-Id"))
        rejected = _request_rejection(request, settings)
        if rejected is not None:
            return rejected
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers.update(SECURITY_RESPONSE_HEADERS)
        _log_request(request, response.status_code, started)
        return response


def _request_id(proposed: str | None) -> str:
    return proposed if proposed and REQUEST_ID_PATTERN.fullmatch(proposed) else str(uuid4())


def _request_rejection(request: Request, settings: Settings) -> JSONResponse | None:
    origin = request.headers.get("Origin")
    allowed_origins = {settings.frontend_origin, str(request.base_url).rstrip("/")}
    if request.method not in SAFE_METHODS and origin and origin not in allowed_origins:
        return _error_response(request, 403, "FORBIDDEN", "Origen no permitido.")
    if _is_disabled_legacy_request(request, settings):
        return _error_response(
            request, 404, "LEGACY_ENDPOINT_DISABLED", "Usá los endpoints autenticados de conversaciones."
        )
    return None


def _is_disabled_legacy_request(request: Request, settings: Settings) -> bool:
    return not settings.legacy_intake_enabled and request.url.path.startswith(LEGACY_PATH_PREFIXES)


def _log_request(request: Request, status_code: int, started: float) -> None:
    logger.info(
        "application_http method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        status_code,
        (time.perf_counter() - started) * 1000,
        request.state.request_id,
    )


def _register_routes(app: FastAPI, settings: Settings) -> None:
    platform_router = platform_routes.router()
    intake_routes = intake_router()
    for route in [*platform_router.routes, *intake_routes.routes]:
        if not isinstance(route, APIRoute):
            continue
        if route.path.startswith(LEGACY_PATH_PREFIXES):
            route.include_in_schema = settings.legacy_intake_enabled
        elif route.path.startswith(V1_PATH_PREFIXES) or route.path.startswith("/conversations"):
            _register_v1_alias(app, route)
            route.include_in_schema = False
    app.include_router(platform_router)
    app.include_router(intake_routes)


def _register_v1_alias(app: FastAPI, route: APIRoute) -> None:
    app.add_api_route(
        "/api/v1" + route.path,
        route.endpoint,
        methods=list(route.methods or []),
        response_model=route.response_model,
        status_code=route.status_code,
        responses=platform_routes.ERROR_RESPONSES,
        tags=route.tags,
        name="v1_" + route.name,
        operation_id="v1_" + route.name,
    )


app = create_app()

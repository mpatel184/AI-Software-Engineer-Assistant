"""Exception handlers mapping domain errors to RFC7807-style JSON responses."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_ctx
from app.domain.exceptions import DomainError

logger = get_logger("errors")


def _safe_validation_errors(exc: RequestValidationError) -> list[dict]:
    """Make pydantic errors JSON-serializable.

    Custom validators raise ValueError, which pydantic v2 stores as an exception
    object inside ``ctx`` — not serializable. Stringify any such context values.
    """
    cleaned: list[dict] = []
    for err in exc.errors():
        item = dict(err)
        ctx = item.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {k: str(v) for k, v in ctx.items()}
        cleaned.append(item)
    return cleaned


def _problem(
    *, status: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    body = {
        "type": f"about:blank#{code}",
        "title": code,
        "status": status,
        "detail": message,
        "request_id": request_id_ctx.get(),
    }
    if details:
        body["errors"] = details
    return JSONResponse(status_code=status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain(_: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            status=exc.status, code=exc.code, message=exc.message, details=exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            status=422,
            code="validation_error",
            message="Request validation failed",
            details={"fields": _safe_validation_errors(exc)},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(status=exc.status_code, code="http_error", message=str(exc.detail))

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc))
        return _problem(
            status=500,
            code="internal_error",
            message="An unexpected error occurred.",
        )

"""FastAPI application factory and lifespan management."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.infrastructure.db.session import engine
from app.presentation.api.v1.router import api_router
from app.presentation.errors import register_exception_handlers
from app.presentation.middleware import RequestContextMiddleware

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("startup", environment=settings.environment, app=settings.app_name)
    yield
    await engine.dispose()
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(debug=settings.debug, json_logs=settings.is_production)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()

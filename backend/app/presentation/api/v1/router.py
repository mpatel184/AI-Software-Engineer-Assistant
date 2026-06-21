"""Aggregates all v1 routers. Feature routers are added here module by module."""
from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.v1 import (
    analyses,
    auth,
    chat,
    documents,
    health,
    reports,
    repositories,
    tests,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(repositories.router)
api_router.include_router(analyses.router)
api_router.include_router(documents.router)
api_router.include_router(tests.router)
api_router.include_router(chat.router)
api_router.include_router(reports.router)

# Feature routers are mounted here as each module is implemented.

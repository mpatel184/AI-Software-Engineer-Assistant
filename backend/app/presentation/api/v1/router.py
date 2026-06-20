"""Aggregates all v1 routers. Feature routers are added here module by module."""
from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.v1 import analyses, auth, health, repositories

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(repositories.router)
api_router.include_router(analyses.router)

# Feature routers (documentation, bugs, ...) are mounted here as each
# module is implemented in subsequent steps.

"""Aggregates all v1 routers. Feature routers are added here module by module."""
from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)

# Feature routers (auth, repositories, analyses, ...) are mounted here as each
# module is implemented in subsequent steps.

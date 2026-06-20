"""Aggregates all v1 routers. Feature routers are added here module by module."""
from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.v1 import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Feature routers (repositories, analyses, ...) are mounted here as each
# module is implemented in subsequent steps.

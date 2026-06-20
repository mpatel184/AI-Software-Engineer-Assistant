"""Shared pytest fixtures and test environment configuration.

Sets minimal env vars so Settings validates without a real .env during unit tests.
"""
from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_swe_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long-xx")
os.environ.setdefault("ENVIRONMENT", "development")

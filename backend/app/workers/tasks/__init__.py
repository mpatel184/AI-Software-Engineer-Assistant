"""Celery task registry. Feature tasks are imported here as modules are built."""
from app.workers.tasks import analysis, cleanup, documentation, indexing

__all__ = ["indexing", "cleanup", "analysis", "documentation"]

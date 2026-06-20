"""Celery-backed implementation of the IndexDispatcher port."""
from __future__ import annotations

import uuid


class CeleryIndexDispatcher:
    """Enqueues the indexing task. Imported lazily to avoid import cycles."""

    def enqueue(self, repo_id: uuid.UUID) -> None:
        from app.workers.tasks.indexing import index_repository

        index_repository.delay(str(repo_id))

    def enqueue_cleanup(self, repo_id: uuid.UUID, clone_path: str | None) -> None:
        from app.workers.tasks.cleanup import cleanup_repository

        cleanup_repository.delay(str(repo_id), clone_path)

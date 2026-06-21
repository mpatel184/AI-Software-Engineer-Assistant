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


class CeleryAnalysisDispatcher:
    """Enqueues the analysis task."""

    def enqueue(self, analysis_id: uuid.UUID) -> None:
        from app.workers.tasks.analysis import run_analysis

        run_analysis.delay(str(analysis_id))


class CeleryDocumentationDispatcher:
    """Enqueues the documentation-generation task."""

    def enqueue(self, document_id: uuid.UUID) -> None:
        from app.workers.tasks.documentation import generate_documentation

        generate_documentation.delay(str(document_id))

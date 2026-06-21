"""Celery task: clone (if needed) and index a repository for RAG."""
from __future__ import annotations

import asyncio
import uuid

from app.application.use_cases.repositories.indexing import IndexingService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.db.repositories.embeddings_metadata_repository import (
    SqlAlchemyEmbeddingsMetadataRepository,
)
from app.infrastructure.db.repositories.repository_repository import (
    SqlAlchemyRepositoryRepository,
)
from app.infrastructure.git.git_client import GitClient
from app.infrastructure.vector.chroma_store import ChromaVectorStore
from app.infrastructure.vector.embedder import build_embedder
from app.workers.celery_app import celery_app
from app.workers.session import task_session

logger = get_logger("worker.indexing")


async def _run(repo_id: uuid.UUID) -> None:
    settings = get_settings()
    async with task_session() as session:
        service = IndexingService(
            repositories=SqlAlchemyRepositoryRepository(session),
            embeddings_meta=SqlAlchemyEmbeddingsMetadataRepository(session),
            git=GitClient(max_size_bytes=settings.max_repo_size_mb * 1024 * 1024),
            embedder=build_embedder(settings),
            vector_store=ChromaVectorStore(
                host=settings.chroma_host, port=settings.chroma_port
            ),
            clone_root=settings.repo_storage_path,
        )
        await service.run(repo_id)


@celery_app.task(
    name="repository.index",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def index_repository(self, repo_id: str) -> None:  # noqa: ANN001
    logger.info("index_task_started", repo_id=repo_id, attempt=self.request.retries)
    try:
        asyncio.run(_run(uuid.UUID(repo_id)))
    except Exception as exc:  # noqa: BLE001
        # Status already set to FAILED by the service; retry transient failures.
        raise self.retry(exc=exc) from exc

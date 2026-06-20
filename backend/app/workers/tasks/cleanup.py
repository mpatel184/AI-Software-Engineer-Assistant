"""Celery task: purge a deleted repository's vectors and cloned files."""
from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.vector.chroma_store import ChromaVectorStore
from app.workers.celery_app import celery_app

logger = get_logger("worker.cleanup")


async def _purge_vectors(repo_id: uuid.UUID) -> None:
    settings = get_settings()
    store = ChromaVectorStore(host=settings.chroma_host, port=settings.chroma_port)
    await store.delete_repository(repo_id=repo_id)


@celery_app.task(name="repository.cleanup", max_retries=2, default_retry_delay=30)
def cleanup_repository(repo_id: str, clone_path: str | None) -> None:
    logger.info("cleanup_started", repo_id=repo_id)
    try:
        asyncio.run(_purge_vectors(uuid.UUID(repo_id)))
    except Exception:  # noqa: BLE001 - best-effort; don't block on vector store
        logger.exception("cleanup_vectors_failed", repo_id=repo_id)

    if clone_path:
        # Guard: only remove paths under the configured storage root.
        root = Path(get_settings().repo_storage_path).resolve()
        target = Path(clone_path).resolve()
        if root == target or root in target.parents:
            shutil.rmtree(target, ignore_errors=True)
        else:
            logger.warning("cleanup_path_outside_root", clone_path=clone_path)

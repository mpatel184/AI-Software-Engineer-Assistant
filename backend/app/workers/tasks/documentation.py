"""Celery task: generate repository documentation."""
from __future__ import annotations

import asyncio
import uuid

from app.application.use_cases.documentation.generate import GenerateDocumentationService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.db.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.db.repositories.repository_repository import (
    SqlAlchemyRepositoryRepository,
)
from app.infrastructure.llm.claude_client import ClaudeLLM
from app.workers.celery_app import celery_app
from app.workers.session import task_session

logger = get_logger("worker.documentation")


async def _run(document_id: uuid.UUID) -> None:
    settings = get_settings()
    async with task_session() as session:
        service = GenerateDocumentationService(
            documents=SqlAlchemyDocumentRepository(session),
            repositories=SqlAlchemyRepositoryRepository(session),
            llm=ClaudeLLM(settings),
        )
        await service.run(document_id)


@celery_app.task(name="documentation.generate", bind=True, max_retries=1, default_retry_delay=20)
def generate_documentation(self, document_id: str) -> None:  # noqa: ANN001
    logger.info("doc_task_started", document_id=document_id)
    try:
        asyncio.run(_run(uuid.UUID(document_id)))
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc

"""Celery task: run a repository analysis."""
from __future__ import annotations

import asyncio
import uuid

from app.application.use_cases.analysis.run import RunAnalysisService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.db.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from app.infrastructure.db.repositories.repository_repository import (
    SqlAlchemyRepositoryRepository,
)
from app.infrastructure.llm.claude_client import ClaudeLLM
from app.workers.celery_app import celery_app
from app.workers.session import task_session

logger = get_logger("worker.analysis")


async def _run(analysis_id: uuid.UUID) -> None:
    settings = get_settings()
    async with task_session() as session:
        service = RunAnalysisService(
            analyses=SqlAlchemyAnalysisRepository(session),
            repositories=SqlAlchemyRepositoryRepository(session),
            llm=ClaudeLLM(settings),
        )
        await service.run(analysis_id)


@celery_app.task(name="analysis.run", bind=True, max_retries=1, default_retry_delay=20)
def run_analysis(self, analysis_id: str) -> None:  # noqa: ANN001
    logger.info("analysis_task_started", analysis_id=analysis_id)
    try:
        asyncio.run(_run(uuid.UUID(analysis_id)))
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc

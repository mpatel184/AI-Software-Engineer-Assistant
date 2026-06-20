"""Analysis management use cases (trigger, get, list) — owner-scoped."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from app.application.interfaces.repositories import (
    AnalysisRepository,
    RepositoryRepository,
)
from app.domain.entities.analysis import Analysis
from app.domain.enums import AnalysisType, JobStatus, RepoStatus
from app.domain.exceptions import NotFoundError, ValidationError


class AnalysisDispatcher(Protocol):
    def enqueue(self, analysis_id: uuid.UUID) -> None: ...


class AnalysisService:
    def __init__(
        self,
        *,
        repositories: RepositoryRepository,
        analyses: AnalysisRepository,
        dispatcher: AnalysisDispatcher,
    ) -> None:
        self._repos = repositories
        self._analyses = analyses
        self._dispatcher = dispatcher

    async def _owned_repo(self, user_id: uuid.UUID, repo_id: uuid.UUID):
        repo = await self._repos.get_for_user(repo_id, user_id)
        if repo is None:
            raise NotFoundError("Repository not found.")
        return repo

    async def trigger(
        self, *, user_id: uuid.UUID, repo_id: uuid.UUID, type: AnalysisType
    ) -> Analysis:
        repo = await self._owned_repo(user_id, repo_id)
        if repo.status is not RepoStatus.READY:
            raise ValidationError("Repository must be fully indexed before analysis.")

        analysis = Analysis(
            id=uuid.uuid4(),
            repository_id=repo_id,
            type=type,
            status=JobStatus.QUEUED,
            created_at=datetime.now(UTC),
        )
        created = await self._analyses.create(analysis)
        self._dispatcher.enqueue(created.id)
        return created

    async def get(self, *, user_id: uuid.UUID, analysis_id: uuid.UUID) -> Analysis:
        analysis = await self._analyses.get(analysis_id)
        if analysis is None:
            raise NotFoundError("Analysis not found.")
        await self._owned_repo(user_id, analysis.repository_id)  # authorization
        return analysis

    async def list(
        self, *, user_id: uuid.UUID, repo_id: uuid.UUID, type: AnalysisType | None
    ) -> list[Analysis]:
        await self._owned_repo(user_id, repo_id)
        return await self._analyses.list_for_repository(repo_id, type=type)

    async def latest(
        self, *, user_id: uuid.UUID, repo_id: uuid.UUID, type: AnalysisType
    ) -> Analysis | None:
        await self._owned_repo(user_id, repo_id)
        return await self._analyses.latest(repo_id, type)

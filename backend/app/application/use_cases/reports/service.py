"""Report generation use cases (generate, get, list) — owner-scoped.

Reports are assembled synchronously from the repository's existing analyses, so
no background job is required. The stored Markdown is the canonical content; PDF
is rendered on demand from it.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.application.interfaces.repositories import (
    AnalysisRepository,
    ReportRepository,
    RepositoryRepository,
)
from app.application.services.report_builder import build_report
from app.domain.entities.report import Report
from app.domain.enums import AnalysisType, JobStatus, ReportType
from app.domain.exceptions import NotFoundError


class ReportService:
    def __init__(
        self,
        *,
        repositories: RepositoryRepository,
        analyses: AnalysisRepository,
        reports: ReportRepository,
    ) -> None:
        self._repos = repositories
        self._analyses = analyses
        self._reports = reports

    async def _owned_repo(self, user_id: uuid.UUID, repo_id: uuid.UUID):
        repo = await self._repos.get_for_user(repo_id, user_id)
        if repo is None:
            raise NotFoundError("Repository not found.")
        return repo

    async def generate(
        self, *, user_id: uuid.UUID, repo_id: uuid.UUID, type: ReportType
    ) -> Report:
        repo = await self._owned_repo(user_id, repo_id)

        architecture = await self._analyses.latest(repo_id, AnalysisType.ARCHITECTURE)
        bugs = await self._analyses.latest(repo_id, AnalysisType.BUGS)
        security = await self._analyses.latest(repo_id, AnalysisType.SECURITY)

        title, content = build_report(
            repo=repo,
            report_type=type,
            architecture=architecture,
            bugs=bugs,
            security=security,
        )

        report = Report(
            id=uuid.uuid4(),
            repository_id=repo_id,
            user_id=user_id,
            type=type,
            title=title,
            content=content,
            status=JobStatus.COMPLETED,
            created_at=datetime.now(UTC),
        )
        return await self._reports.create(report)

    async def get(self, *, user_id: uuid.UUID, report_id: uuid.UUID) -> Report:
        report = await self._reports.get(report_id)
        if report is None:
            raise NotFoundError("Report not found.")
        await self._owned_repo(user_id, report.repository_id)  # authorization
        return report

    async def list(self, *, user_id: uuid.UUID, repo_id: uuid.UUID) -> list[Report]:
        await self._owned_repo(user_id, repo_id)
        return await self._reports.list_for_repository(repo_id)

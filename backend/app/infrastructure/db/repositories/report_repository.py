"""SQLAlchemy implementation of ReportRepository."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.report import Report
from app.infrastructure.db.models.report import ReportModel


def _to_entity(m: ReportModel) -> Report:
    return Report(
        id=m.id,
        repository_id=m.repository_id,
        user_id=m.user_id,
        type=m.type,
        title=m.title,
        content=m.content,
        status=m.status,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, report: Report) -> Report:
        model = ReportModel(
            id=report.id,
            repository_id=report.repository_id,
            user_id=report.user_id,
            type=report.type,
            title=report.title,
            content=report.content,
            status=report.status,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get(self, report_id: uuid.UUID) -> Report | None:
        model = await self._session.get(ReportModel, report_id)
        return _to_entity(model) if model else None

    async def list_for_repository(self, repo_id: uuid.UUID) -> list[Report]:
        result = await self._session.execute(
            select(ReportModel)
            .where(ReportModel.repository_id == repo_id)
            .order_by(ReportModel.created_at.desc())
        )
        return [_to_entity(m) for m in result.scalars().all()]

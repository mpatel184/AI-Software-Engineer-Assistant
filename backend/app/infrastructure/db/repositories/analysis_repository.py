"""SQLAlchemy implementation of AnalysisRepository."""
from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.analysis import Analysis
from app.domain.enums import AnalysisType, JobStatus
from app.infrastructure.db.models.analysis import AnalysisModel


def _to_entity(m: AnalysisModel) -> Analysis:
    return Analysis(
        id=m.id,
        repository_id=m.repository_id,
        type=m.type,
        status=m.status,
        summary=m.summary or {},
        metrics=m.metrics or {},
        score=m.score,
        error_message=m.error_message,
        started_at=m.started_at,
        completed_at=m.completed_at,
        created_at=m.created_at,
    )


class SqlAlchemyAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, analysis: Analysis) -> Analysis:
        from datetime import UTC, datetime

        model = AnalysisModel(
            id=analysis.id,
            repository_id=analysis.repository_id,
            type=analysis.type,
            status=analysis.status,
            summary=analysis.summary,
            metrics=analysis.metrics,
            score=analysis.score,
            created_at=analysis.created_at or datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get(self, analysis_id: uuid.UUID) -> Analysis | None:
        model = await self._session.get(AnalysisModel, analysis_id)
        return _to_entity(model) if model else None

    async def update(self, analysis: Analysis) -> Analysis:
        model = await self._session.get(AnalysisModel, analysis.id)
        if model is None:
            raise ValueError("Analysis not found for update.")
        model.status = analysis.status
        model.summary = analysis.summary
        model.metrics = analysis.metrics
        model.score = analysis.score
        model.error_message = analysis.error_message
        model.started_at = analysis.started_at
        model.completed_at = analysis.completed_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_for_repository(
        self, repo_id: uuid.UUID, *, type: AnalysisType | None = None
    ) -> list[Analysis]:
        stmt = select(AnalysisModel).where(AnalysisModel.repository_id == repo_id)
        if type is not None:
            stmt = stmt.where(AnalysisModel.type == type)
        stmt = stmt.order_by(AnalysisModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def latest(self, repo_id: uuid.UUID, type: AnalysisType) -> Analysis | None:
        result = await self._session.execute(
            select(AnalysisModel)
            .where(AnalysisModel.repository_id == repo_id, AnalysisModel.type == type)
            .order_by(AnalysisModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def update_status(
        self, analysis_id: uuid.UUID, status: JobStatus, *, error_message: str | None = None
    ) -> None:
        await self._session.execute(
            update(AnalysisModel)
            .where(AnalysisModel.id == analysis_id)
            .values(status=status, error_message=error_message)
        )
        await self._session.flush()

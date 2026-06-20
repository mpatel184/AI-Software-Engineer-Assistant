"""SQLAlchemy implementation of RepositoryRepository."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositories import RepositoryListResult
from app.domain.entities.repository import Repository
from app.domain.enums import RepoStatus
from app.infrastructure.db.models.repository import RepositoryModel


def _to_entity(m: RepositoryModel) -> Repository:
    return Repository(
        id=m.id,
        user_id=m.user_id,
        name=m.name,
        source=m.source,
        status=m.status,
        github_url=m.github_url,
        default_branch=m.default_branch,
        clone_path=m.clone_path,
        primary_language=m.primary_language,
        languages=m.languages or {},
        file_count=m.file_count,
        total_lines=m.total_lines,
        size_bytes=m.size_bytes,
        commit_sha=m.commit_sha,
        error_message=m.error_message,
        indexed_at=m.indexed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyRepositoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, repository: Repository) -> Repository:
        model = RepositoryModel(
            id=repository.id,
            user_id=repository.user_id,
            name=repository.name,
            source=repository.source,
            status=repository.status,
            github_url=repository.github_url,
            clone_path=repository.clone_path,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get(self, repo_id: uuid.UUID) -> Repository | None:
        model = await self._session.get(RepositoryModel, repo_id)
        return _to_entity(model) if model else None

    async def get_for_user(
        self, repo_id: uuid.UUID, user_id: uuid.UUID
    ) -> Repository | None:
        result = await self._session.execute(
            select(RepositoryModel).where(
                RepositoryModel.id == repo_id, RepositoryModel.user_id == user_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: RepoStatus | None = None,
        search: str | None = None,
        limit: int,
        offset: int,
        sort_desc: bool = True,
    ) -> RepositoryListResult:
        filters = [RepositoryModel.user_id == user_id]
        if status is not None:
            filters.append(RepositoryModel.status == status)
        if search:
            like = f"%{search}%"
            filters.append(
                RepositoryModel.name.ilike(like) | RepositoryModel.github_url.ilike(like)
            )

        total = await self._session.scalar(
            select(func.count()).select_from(RepositoryModel).where(*filters)
        )
        order = (
            RepositoryModel.created_at.desc() if sort_desc else RepositoryModel.created_at.asc()
        )
        result = await self._session.execute(
            select(RepositoryModel).where(*filters).order_by(order).limit(limit).offset(offset)
        )
        items = [_to_entity(m) for m in result.scalars().all()]
        return RepositoryListResult(items=items, total=total or 0)

    async def update(self, repository: Repository) -> Repository:
        model = await self._session.get(RepositoryModel, repository.id)
        if model is None:
            raise ValueError("Repository not found for update.")
        model.name = repository.name
        model.status = repository.status
        model.default_branch = repository.default_branch
        model.clone_path = repository.clone_path
        model.primary_language = repository.primary_language
        model.languages = repository.languages
        model.file_count = repository.file_count
        model.total_lines = repository.total_lines
        model.size_bytes = repository.size_bytes
        model.commit_sha = repository.commit_sha
        model.error_message = repository.error_message
        model.indexed_at = repository.indexed_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update_status(
        self, repo_id: uuid.UUID, status: RepoStatus, *, error_message: str | None = None
    ) -> None:
        await self._session.execute(
            update(RepositoryModel)
            .where(RepositoryModel.id == repo_id)
            .values(status=status, error_message=error_message)
        )
        await self._session.flush()

    async def delete(self, repo_id: uuid.UUID) -> None:
        model = await self._session.get(RepositoryModel, repo_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

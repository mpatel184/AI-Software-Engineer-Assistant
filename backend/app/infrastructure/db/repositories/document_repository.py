"""SQLAlchemy implementation of DocumentRepository."""
from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.document import Document
from app.domain.enums import DocumentFormat, DocumentType, JobStatus
from app.infrastructure.db.models.document import DocumentModel


def _to_entity(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        repository_id=m.repository_id,
        type=m.type,
        title=m.title,
        content=m.content,
        format=m.format,
        status=m.status,
        error_message=m.error_message,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_placeholder(
        self, repo_id: uuid.UUID, type: DocumentType, title: str
    ) -> Document:
        existing = await self.get_by_type(repo_id, type)
        if existing is not None:
            model = await self._session.get(DocumentModel, existing.id)
            assert model is not None
            model.status = JobStatus.QUEUED
            model.error_message = None
            model.title = title
            await self._session.flush()
            await self._session.refresh(model)
            return _to_entity(model)

        model = DocumentModel(
            id=uuid.uuid4(),
            repository_id=repo_id,
            type=type,
            title=title,
            content="",
            format=DocumentFormat.MARKDOWN,
            status=JobStatus.QUEUED,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get(self, document_id: uuid.UUID) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return _to_entity(model) if model else None

    async def get_by_type(
        self, repo_id: uuid.UUID, type: DocumentType
    ) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.repository_id == repo_id, DocumentModel.type == type
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_for_repository(self, repo_id: uuid.UUID) -> list[Document]:
        result = await self._session.execute(
            select(DocumentModel)
            .where(DocumentModel.repository_id == repo_id)
            .order_by(DocumentModel.type)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def update(self, document: Document) -> Document:
        model = await self._session.get(DocumentModel, document.id)
        if model is None:
            raise ValueError("Document not found for update.")
        model.title = document.title
        model.content = document.content
        model.format = document.format
        model.status = document.status
        model.error_message = document.error_message
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update_status(
        self, document_id: uuid.UUID, status: JobStatus, *, error_message: str | None = None
    ) -> None:
        await self._session.execute(
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(status=status, error_message=error_message)
        )
        await self._session.flush()

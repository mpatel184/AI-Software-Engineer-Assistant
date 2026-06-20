"""SQLAlchemy implementation of EmbeddingsMetadataRepository."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.vector import Chunk
from app.infrastructure.db.models.repository import EmbeddingsMetadataModel


class SqlAlchemyEmbeddingsMetadataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_add(
        self, repo_id: uuid.UUID, chunks: list[Chunk], chroma_ids: list[str]
    ) -> None:
        self._session.add_all(
            [
                EmbeddingsMetadataModel(
                    id=uuid.uuid4(),
                    repository_id=repo_id,
                    chroma_id=chroma_id,
                    file_path=chunk.file_path,
                    language=chunk.language,
                    chunk_index=chunk.chunk_index,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    token_count=chunk.token_count,
                    content_hash=chunk.content_hash,
                )
                for chunk, chroma_id in zip(chunks, chroma_ids, strict=True)
            ]
        )
        await self._session.flush()

    async def delete_for_repository(self, repo_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(EmbeddingsMetadataModel).where(
                EmbeddingsMetadataModel.repository_id == repo_id
            )
        )
        await self._session.flush()

    async def count_for_repository(self, repo_id: uuid.UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(EmbeddingsMetadataModel)
            .where(EmbeddingsMetadataModel.repository_id == repo_id)
        )
        return total or 0

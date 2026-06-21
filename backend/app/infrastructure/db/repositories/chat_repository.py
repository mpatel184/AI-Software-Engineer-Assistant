"""SQLAlchemy implementation of ChatMessageRepository."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chat import ChatMessage, ChatSource
from app.infrastructure.db.models.chat import ChatMessageModel


def _to_entity(m: ChatMessageModel) -> ChatMessage:
    return ChatMessage(
        id=m.id,
        repository_id=m.repository_id,
        user_id=m.user_id,
        role=m.role,
        content=m.content,
        sources=[
            ChatSource(
                file_path=str(s.get("file_path", "")),
                start_line=int(s.get("start_line", 0)),
                end_line=int(s.get("end_line", 0)),
            )
            for s in (m.sources or [])
        ],
        created_at=m.created_at,
    )


class SqlAlchemyChatMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: ChatMessage) -> ChatMessage:
        model = ChatMessageModel(
            id=message.id,
            repository_id=message.repository_id,
            user_id=message.user_id,
            role=message.role,
            content=message.content,
            sources=[
                {
                    "file_path": s.file_path,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                }
                for s in message.sources
            ],
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def list_for_repository(
        self, repo_id: uuid.UUID, user_id: uuid.UUID, *, limit: int = 100
    ) -> list[ChatMessage]:
        result = await self._session.execute(
            select(ChatMessageModel)
            .where(
                ChatMessageModel.repository_id == repo_id,
                ChatMessageModel.user_id == user_id,
            )
            .order_by(ChatMessageModel.created_at.asc())
            .limit(limit)
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def recent_pairs(
        self, repo_id: uuid.UUID, user_id: uuid.UUID, *, limit: int = 6
    ) -> list[ChatMessage]:
        """Most recent messages (chronological order) for conversational context."""
        result = await self._session.execute(
            select(ChatMessageModel)
            .where(
                ChatMessageModel.repository_id == repo_id,
                ChatMessageModel.user_id == user_id,
            )
            .order_by(ChatMessageModel.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return [_to_entity(m) for m in rows]

    async def clear_for_repository(
        self, repo_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        await self._session.execute(
            delete(ChatMessageModel).where(
                ChatMessageModel.repository_id == repo_id,
                ChatMessageModel.user_id == user_id,
            )
        )
        await self._session.flush()

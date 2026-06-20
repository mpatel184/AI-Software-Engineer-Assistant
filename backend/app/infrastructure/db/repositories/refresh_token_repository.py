"""SQLAlchemy implementation of RefreshTokenRepository."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.user import RefreshTokenModel


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> None:
        self._session.add(
            RefreshTokenModel(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        await self._session.flush()

    async def get_active(self, token_hash: str) -> tuple[uuid.UUID, datetime] | None:
        result = await self._session.execute(
            select(RefreshTokenModel.user_id, RefreshTokenModel.expires_at).where(
                RefreshTokenModel.token_hash == token_hash,
                RefreshTokenModel.revoked.is_(False),
                RefreshTokenModel.expires_at > datetime.now(UTC),
            )
        )
        row = result.first()
        return (row[0], row[1]) if row else None

    async def revoke(self, token_hash: str) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(revoked=True)
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked.is_(False))
            .values(revoked=True)
        )

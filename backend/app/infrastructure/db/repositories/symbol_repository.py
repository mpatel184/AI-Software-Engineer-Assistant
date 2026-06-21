"""SQLAlchemy implementation of SymbolRepository."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.symbol import Symbol
from app.domain.enums import SymbolKind
from app.infrastructure.db.models.symbol import SymbolModel


def _to_entity(m: SymbolModel) -> Symbol:
    return Symbol(
        id=m.id,
        repository_id=m.repository_id,
        file_path=m.file_path,
        kind=m.kind,
        name=m.name,
        qualified_name=m.qualified_name,
        signature=m.signature,
        start_line=m.start_line,
        end_line=m.end_line,
        language=m.language,
        parent_name=m.parent_name,
        docstring=m.docstring,
    )


class SqlAlchemySymbolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_add(self, symbols: list[Symbol]) -> None:
        if not symbols:
            return
        self._session.add_all(
            [
                SymbolModel(
                    id=s.id,
                    repository_id=s.repository_id,
                    file_path=s.file_path,
                    kind=s.kind,
                    name=s.name,
                    qualified_name=s.qualified_name,
                    signature=s.signature,
                    start_line=s.start_line,
                    end_line=s.end_line,
                    language=s.language,
                    parent_name=s.parent_name,
                    docstring=s.docstring,
                )
                for s in symbols
            ]
        )
        await self._session.flush()

    async def delete_for_repository(self, repo_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(SymbolModel).where(SymbolModel.repository_id == repo_id)
        )
        await self._session.flush()

    async def count_for_repository(self, repo_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(SymbolModel)
            .where(SymbolModel.repository_id == repo_id)
        )
        return int(result.scalar_one())

    async def search(
        self,
        repo_id: uuid.UUID,
        query: str,
        *,
        kinds: list[SymbolKind] | None = None,
        limit: int = 10,
    ) -> list[Symbol]:
        term = f"%{query.strip()}%"
        stmt = select(SymbolModel).where(
            SymbolModel.repository_id == repo_id,
            or_(
                SymbolModel.name.ilike(term),
                SymbolModel.qualified_name.ilike(term),
            ),
        )
        if kinds:
            stmt = stmt.where(SymbolModel.kind.in_(kinds))
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

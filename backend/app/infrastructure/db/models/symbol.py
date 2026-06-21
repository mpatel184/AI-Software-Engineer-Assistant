"""ORM model for the code symbol index."""
from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import SymbolKind
from app.infrastructure.db.base import Base, UUIDMixin


class SymbolModel(UUIDMixin, Base):
    __tablename__ = "symbols"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    kind: Mapped[SymbolKind] = mapped_column(
        Enum(SymbolKind, name="symbol_kind", native_enum=True), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    qualified_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False, default="")
    start_line: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language: Mapped[str | None] = mapped_column(String(50))
    parent_name: Mapped[str | None] = mapped_column(String(500))
    docstring: Mapped[str | None] = mapped_column(Text)

    repository = relationship("RepositoryModel")

    __table_args__ = (
        Index("ix_symbols_repo_name", "repository_id", "name"),
        Index("ix_symbols_repo_kind", "repository_id", "kind"),
    )

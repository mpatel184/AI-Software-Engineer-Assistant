"""ORM models for repositories and embeddings metadata."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import RepoSource, RepoStatus
from app.infrastructure.db.base import Base, TimestampMixin, UUIDMixin


class RepositoryModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "repositories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[RepoSource] = mapped_column(
        Enum(RepoSource, name="repo_source", native_enum=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    github_url: Mapped[str | None] = mapped_column(String(500))
    default_branch: Mapped[str | None] = mapped_column(String(200))
    clone_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RepoStatus] = mapped_column(
        Enum(RepoStatus, name="repo_status", native_enum=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=RepoStatus.PENDING,
        server_default=RepoStatus.PENDING.value,
    )
    primary_language: Mapped[str | None] = mapped_column(String(50))
    languages: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_lines: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    commit_sha: Mapped[str | None] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(Text)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    embeddings: Mapped[list["EmbeddingsMetadataModel"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_repositories_user_id", "user_id"),
        Index("ix_repositories_user_status", "user_id", "status"),
    )


class EmbeddingsMetadataModel(UUIDMixin, Base):
    __tablename__ = "embeddings_metadata"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    chroma_id: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    language: Mapped[str | None] = mapped_column(String(50))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    repository: Mapped["RepositoryModel"] = relationship(back_populates="embeddings")

    __table_args__ = (
        Index("ix_embeddings_repo_id", "repository_id"),
        Index("ix_embeddings_repo_file", "repository_id", "file_path"),
        Index("uq_embeddings_repo_chroma", "repository_id", "chroma_id", unique=True),
    )

"""ORM model for generated documentation."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import DocumentFormat, DocumentType, JobStatus
from app.infrastructure.db.base import Base, TimestampMixin, UUIDMixin


class DocumentModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", native_enum=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    format: Mapped[DocumentFormat] = mapped_column(
        Enum(DocumentFormat, name="document_format", native_enum=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=DocumentFormat.MARKDOWN,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=JobStatus.QUEUED,
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    repository = relationship("RepositoryModel")

    __table_args__ = (
        Index("uq_documents_repo_type", "repository_id", "type", unique=True),
    )

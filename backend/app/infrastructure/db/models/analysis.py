"""ORM model for repository analyses."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import AnalysisType, JobStatus
from app.infrastructure.db.base import Base, UUIDMixin


class AnalysisModel(UUIDMixin, Base):
    __tablename__ = "analyses"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[AnalysisType] = mapped_column(
        Enum(AnalysisType, name="analysis_type", native_enum=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=JobStatus.QUEUED,
    )
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    score: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    repository = relationship("RepositoryModel")

    __table_args__ = (
        Index("ix_analyses_repo_type", "repository_id", "type"),
        Index("ix_analyses_repo_created", "repository_id", "created_at"),
    )

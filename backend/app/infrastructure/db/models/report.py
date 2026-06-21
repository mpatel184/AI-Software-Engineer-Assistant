"""ORM model for aggregated repository reports."""
from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import JobStatus, ReportType
from app.infrastructure.db.base import Base, TimestampMixin, UUIDMixin


class ReportModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ReportType] = mapped_column(
        Enum(ReportType, name="report_type", native_enum=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=True),
        nullable=False,
        default=JobStatus.COMPLETED,
    )

    repository = relationship("RepositoryModel")

    __table_args__ = (
        Index("ix_reports_repo_created", "repository_id", "created_at"),
    )

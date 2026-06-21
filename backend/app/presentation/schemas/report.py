"""Request/response schemas for the reports module."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import JobStatus, ReportType


class GenerateReportRequest(BaseModel):
    type: ReportType = ReportType.FULL


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    type: ReportType
    title: str
    content: str
    status: JobStatus
    created_at: datetime | None
    updated_at: datetime | None


class ReportSummary(BaseModel):
    """List item without the (large) content body."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    type: ReportType
    title: str
    status: JobStatus
    created_at: datetime | None
    updated_at: datetime | None

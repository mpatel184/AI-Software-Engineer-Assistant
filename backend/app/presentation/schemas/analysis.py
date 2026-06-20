"""Request/response schemas for the analysis module."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import AnalysisType, JobStatus


class TriggerAnalysisRequest(BaseModel):
    type: AnalysisType = AnalysisType.ARCHITECTURE


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    type: AnalysisType
    status: JobStatus
    summary: dict
    metrics: dict
    score: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime | None

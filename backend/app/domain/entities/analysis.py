"""Analysis domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import AnalysisType, JobStatus


@dataclass(slots=True)
class Analysis:
    id: uuid.UUID
    repository_id: uuid.UUID
    type: AnalysisType
    status: JobStatus
    summary: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    score: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

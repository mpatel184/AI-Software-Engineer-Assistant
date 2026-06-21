"""Report domain entity (aggregated, exportable repository report)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import JobStatus, ReportType


@dataclass(slots=True)
class Report:
    id: uuid.UUID
    repository_id: uuid.UUID
    user_id: uuid.UUID
    type: ReportType
    title: str
    content: str
    status: JobStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None

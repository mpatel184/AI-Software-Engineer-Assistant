"""Document domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import DocumentFormat, DocumentType, JobStatus


@dataclass(slots=True)
class Document:
    id: uuid.UUID
    repository_id: uuid.UUID
    type: DocumentType
    title: str
    content: str
    format: DocumentFormat
    status: JobStatus
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

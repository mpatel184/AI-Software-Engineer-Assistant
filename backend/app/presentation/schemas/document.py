"""Request/response schemas for the documentation module."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import DocumentFormat, DocumentType, JobStatus


class GenerateDocumentRequest(BaseModel):
    type: DocumentType = DocumentType.README


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    type: DocumentType
    title: str
    content: str
    format: DocumentFormat
    status: JobStatus
    error_message: str | None
    created_at: datetime | None
    updated_at: datetime | None


class DocumentSummary(BaseModel):
    """List item without the (potentially large) content body."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    type: DocumentType
    title: str
    format: DocumentFormat
    status: JobStatus
    error_message: str | None
    created_at: datetime | None
    updated_at: datetime | None

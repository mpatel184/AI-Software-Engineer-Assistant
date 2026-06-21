"""Request/response schemas for the RAG chat module."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ChatRole


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_path: str
    start_line: int
    end_line: int


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    role: ChatRole
    content: str
    sources: list[ChatSourceResponse]
    created_at: datetime | None

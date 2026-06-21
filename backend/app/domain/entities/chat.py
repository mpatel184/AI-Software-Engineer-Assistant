"""Chat message domain entity for repository-aware RAG chat."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import ChatRole


@dataclass(slots=True)
class ChatSource:
    """A repository chunk cited as grounding for an assistant answer."""

    file_path: str
    start_line: int
    end_line: int


@dataclass(slots=True)
class ChatMessage:
    id: uuid.UUID
    repository_id: uuid.UUID
    user_id: uuid.UUID
    role: ChatRole
    content: str
    sources: list[ChatSource] = field(default_factory=list)
    created_at: datetime | None = None

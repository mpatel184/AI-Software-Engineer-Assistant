"""Repository domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import RepoSource, RepoStatus


@dataclass(slots=True)
class Repository:
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    source: RepoSource
    status: RepoStatus
    github_url: str | None = None
    default_branch: str | None = None
    clone_path: str | None = None
    primary_language: str | None = None
    languages: dict[str, float] = field(default_factory=dict)
    file_count: int = 0
    total_lines: int = 0
    size_bytes: int = 0
    commit_sha: str | None = None
    error_message: str | None = None
    indexed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_ready(self) -> bool:
        return self.status is RepoStatus.READY

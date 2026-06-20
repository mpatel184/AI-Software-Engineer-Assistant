"""Request/response schemas for the repository module."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import RepoSource, RepoStatus


class CreateRepositoryFromGitHubRequest(BaseModel):
    github_url: str = Field(max_length=500)
    name: str | None = Field(default=None, max_length=200)


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source: RepoSource
    status: RepoStatus
    github_url: str | None
    default_branch: str | None
    primary_language: str | None
    languages: dict[str, float]
    file_count: int
    total_lines: int
    size_bytes: int
    commit_sha: str | None
    error_message: str | None
    indexed_at: datetime | None
    created_at: datetime | None
    # NOTE: clone_path is intentionally excluded — it is server-internal.

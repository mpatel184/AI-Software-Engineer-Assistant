"""Repository ports for the auth module.

Concrete SQLAlchemy implementations live in infrastructure/db/repositories.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.application.interfaces.vector import Chunk
from app.domain.entities.analysis import Analysis
from app.domain.entities.chat import ChatMessage
from app.domain.entities.document import Document
from app.domain.entities.report import Report
from app.domain.entities.repository import Repository
from app.domain.entities.symbol import Symbol
from app.domain.entities.user import User
from app.domain.enums import (
    AnalysisType,
    DocumentType,
    JobStatus,
    RepoStatus,
    SymbolKind,
)


class UserRepository(Protocol):
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def create(self, user: User) -> User: ...
    async def update(self, user: User) -> User: ...


class RefreshTokenRepository(Protocol):
    async def add(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> None: ...
    async def get_active(self, token_hash: str) -> tuple[uuid.UUID, datetime] | None: ...
    async def revoke(self, token_hash: str) -> None: ...
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None: ...


@dataclass(slots=True)
class RepositoryListResult:
    items: list[Repository]
    total: int


class RepositoryRepository(Protocol):
    async def create(self, repository: Repository) -> Repository: ...
    async def get(self, repo_id: uuid.UUID) -> Repository | None: ...
    async def get_for_user(
        self, repo_id: uuid.UUID, user_id: uuid.UUID
    ) -> Repository | None: ...
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: RepoStatus | None = None,
        search: str | None = None,
        limit: int,
        offset: int,
        sort_desc: bool = True,
    ) -> RepositoryListResult: ...
    async def update(self, repository: Repository) -> Repository: ...
    async def update_status(
        self, repo_id: uuid.UUID, status: RepoStatus, *, error_message: str | None = None
    ) -> None: ...
    async def delete(self, repo_id: uuid.UUID) -> None: ...


class EmbeddingsMetadataRepository(Protocol):
    async def bulk_add(self, repo_id: uuid.UUID, chunks: list[Chunk], chroma_ids: list[str]) -> None: ...
    async def delete_for_repository(self, repo_id: uuid.UUID) -> None: ...
    async def count_for_repository(self, repo_id: uuid.UUID) -> int: ...


class AnalysisRepository(Protocol):
    async def create(self, analysis: Analysis) -> Analysis: ...
    async def get(self, analysis_id: uuid.UUID) -> Analysis | None: ...
    async def update(self, analysis: Analysis) -> Analysis: ...
    async def list_for_repository(
        self, repo_id: uuid.UUID, *, type: AnalysisType | None = None
    ) -> list[Analysis]: ...
    async def latest(
        self, repo_id: uuid.UUID, type: AnalysisType
    ) -> Analysis | None: ...
    async def update_status(
        self, analysis_id: uuid.UUID, status: JobStatus, *, error_message: str | None = None
    ) -> None: ...


class SymbolRepository(Protocol):
    async def bulk_add(self, symbols: list[Symbol]) -> None: ...
    async def delete_for_repository(self, repo_id: uuid.UUID) -> None: ...
    async def count_for_repository(self, repo_id: uuid.UUID) -> int: ...
    async def search(
        self,
        repo_id: uuid.UUID,
        query: str,
        *,
        kinds: list[SymbolKind] | None = None,
        limit: int = 10,
    ) -> list[Symbol]: ...


class ReportRepository(Protocol):
    async def create(self, report: Report) -> Report: ...
    async def get(self, report_id: uuid.UUID) -> Report | None: ...
    async def list_for_repository(self, repo_id: uuid.UUID) -> list[Report]: ...


class ChatMessageRepository(Protocol):
    async def add(self, message: ChatMessage) -> ChatMessage: ...
    async def list_for_repository(
        self, repo_id: uuid.UUID, user_id: uuid.UUID, *, limit: int = 100
    ) -> list[ChatMessage]: ...
    async def recent_pairs(
        self, repo_id: uuid.UUID, user_id: uuid.UUID, *, limit: int = 6
    ) -> list[ChatMessage]: ...
    async def clear_for_repository(
        self, repo_id: uuid.UUID, user_id: uuid.UUID
    ) -> None: ...


class DocumentRepository(Protocol):
    async def upsert_placeholder(
        self, repo_id: uuid.UUID, type: DocumentType, title: str
    ) -> Document: ...
    async def get(self, document_id: uuid.UUID) -> Document | None: ...
    async def get_by_type(
        self, repo_id: uuid.UUID, type: DocumentType
    ) -> Document | None: ...
    async def list_for_repository(self, repo_id: uuid.UUID) -> list[Document]: ...
    async def update(self, document: Document) -> Document: ...
    async def update_status(
        self, document_id: uuid.UUID, status: JobStatus, *, error_message: str | None = None
    ) -> None: ...

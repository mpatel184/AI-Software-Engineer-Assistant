"""Documentation management use cases (trigger, get, list) — owner-scoped."""
from __future__ import annotations

import uuid
from typing import Protocol

from app.application.interfaces.repositories import (
    DocumentRepository,
    RepositoryRepository,
)
from app.domain.entities.document import Document
from app.domain.enums import DocumentType, RepoStatus
from app.domain.exceptions import NotFoundError, ValidationError

_TITLES = {
    DocumentType.README: "README",
    DocumentType.API_DOCS: "API Documentation",
    DocumentType.FUNCTION_DOCS: "Function Reference",
    DocumentType.CLASS_DOCS: "Class Reference",
}


class DocumentationDispatcher(Protocol):
    def enqueue(self, document_id: uuid.UUID) -> None: ...


class DocumentationService:
    def __init__(
        self,
        *,
        repositories: RepositoryRepository,
        documents: DocumentRepository,
        dispatcher: DocumentationDispatcher,
    ) -> None:
        self._repos = repositories
        self._docs = documents
        self._dispatcher = dispatcher

    async def _owned_repo(self, user_id: uuid.UUID, repo_id: uuid.UUID):
        repo = await self._repos.get_for_user(repo_id, user_id)
        if repo is None:
            raise NotFoundError("Repository not found.")
        return repo

    async def generate(
        self, *, user_id: uuid.UUID, repo_id: uuid.UUID, type: DocumentType
    ) -> Document:
        repo = await self._owned_repo(user_id, repo_id)
        if repo.status is not RepoStatus.READY:
            raise ValidationError("Repository must be fully indexed before generating docs.")

        document = await self._docs.upsert_placeholder(repo_id, type, _TITLES[type])
        self._dispatcher.enqueue(document.id)
        return document

    async def get(self, *, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        document = await self._docs.get(document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        await self._owned_repo(user_id, document.repository_id)
        return document

    async def list(self, *, user_id: uuid.UUID, repo_id: uuid.UUID) -> list[Document]:
        await self._owned_repo(user_id, repo_id)
        return await self._docs.list_for_repository(repo_id)

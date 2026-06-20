"""Repository management use cases (create, list, get, delete, reindex).

Owner-scoped throughout: every read/mutation is checked against the requesting
user to prevent unauthorized repository access. Indexing itself is dispatched to
the background worker via the injected task dispatcher.
"""
from __future__ import annotations

import uuid
from typing import Protocol

from app.application.interfaces.repositories import (
    RepositoryListResult,
    RepositoryRepository,
)
from app.core.security import validate_github_url
from app.domain.entities.repository import Repository
from app.domain.enums import RepoSource, RepoStatus
from app.domain.exceptions import AlreadyExistsError, NotFoundError, ValidationError


class IndexDispatcher(Protocol):
    """Port for enqueuing background repository jobs."""

    def enqueue(self, repo_id: uuid.UUID) -> None: ...
    def enqueue_cleanup(self, repo_id: uuid.UUID, clone_path: str | None) -> None: ...


class RepositoryService:
    def __init__(
        self,
        *,
        repositories: RepositoryRepository,
        dispatcher: IndexDispatcher,
    ) -> None:
        self._repos = repositories
        self._dispatcher = dispatcher

    async def create_from_github(
        self, *, user_id: uuid.UUID, github_url: str, name: str | None
    ) -> Repository:
        owner, repo_name = validate_github_url(github_url)
        normalized_url = f"https://github.com/{owner}/{repo_name}"

        existing = await self._repos.list_for_user(
            user_id, search=normalized_url, limit=1, offset=0
        )
        if any(r.github_url == normalized_url for r in existing.items):
            raise AlreadyExistsError("You have already added this repository.")

        repository = Repository(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name or repo_name,
            source=RepoSource.GITHUB,
            status=RepoStatus.PENDING,
            github_url=normalized_url,
        )
        created = await self._repos.create(repository)
        self._dispatcher.enqueue(created.id)
        return created

    async def create_from_upload(
        self, *, user_id: uuid.UUID, name: str, clone_path: str
    ) -> Repository:
        repository = Repository(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            source=RepoSource.UPLOAD,
            status=RepoStatus.PENDING,
            clone_path=clone_path,
        )
        created = await self._repos.create(repository)
        self._dispatcher.enqueue(created.id)
        return created

    async def list(
        self,
        *,
        user_id: uuid.UUID,
        status: RepoStatus | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> RepositoryListResult:
        return await self._repos.list_for_user(
            user_id, status=status, search=search, limit=limit, offset=offset
        )

    async def get(self, *, user_id: uuid.UUID, repo_id: uuid.UUID) -> Repository:
        repo = await self._repos.get_for_user(repo_id, user_id)
        if repo is None:
            raise NotFoundError("Repository not found.")
        return repo

    async def delete(self, *, user_id: uuid.UUID, repo_id: uuid.UUID) -> Repository:
        repo = await self.get(user_id=user_id, repo_id=repo_id)
        # Purge vectors + on-disk clone asynchronously; DB cascade handles metadata.
        self._dispatcher.enqueue_cleanup(repo.id, repo.clone_path)
        await self._repos.delete(repo.id)
        return repo

    async def reindex(self, *, user_id: uuid.UUID, repo_id: uuid.UUID) -> Repository:
        repo = await self.get(user_id=user_id, repo_id=repo_id)
        if repo.status in (RepoStatus.CLONING, RepoStatus.INDEXING):
            raise ValidationError("Repository is already being processed.")
        await self._repos.update_status(repo.id, RepoStatus.PENDING)
        self._dispatcher.enqueue(repo.id)
        return repo

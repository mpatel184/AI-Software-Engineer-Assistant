"""Unit tests for RepositoryService (owner-scoping, dispatch, validation)."""
from __future__ import annotations

import uuid

import pytest

from app.application.interfaces.repositories import RepositoryListResult
from app.application.use_cases.repositories.service import RepositoryService
from app.domain.entities.repository import Repository
from app.domain.enums import RepoSource, RepoStatus
from app.domain.exceptions import AlreadyExistsError, NotFoundError, ValidationError


class FakeRepoRepo:
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, Repository] = {}
        self.status_updates: list[tuple[uuid.UUID, RepoStatus]] = []

    async def create(self, repository):
        self.items[repository.id] = repository
        return repository

    async def get(self, repo_id):
        return self.items.get(repo_id)

    async def get_for_user(self, repo_id, user_id):
        repo = self.items.get(repo_id)
        return repo if repo and repo.user_id == user_id else None

    async def list_for_user(self, user_id, *, status=None, search=None, limit=20, offset=0, sort_desc=True):
        items = [r for r in self.items.values() if r.user_id == user_id]
        if search:
            items = [r for r in items if (r.github_url and search in r.github_url) or search in r.name]
        return RepositoryListResult(items=items, total=len(items))

    async def update(self, repository):
        self.items[repository.id] = repository
        return repository

    async def update_status(self, repo_id, status, *, error_message=None):
        self.status_updates.append((repo_id, status))
        if repo_id in self.items:
            self.items[repo_id].status = status

    async def delete(self, repo_id):
        self.items.pop(repo_id, None)


class FakeDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[uuid.UUID] = []
        self.cleanups: list[tuple[uuid.UUID, str | None]] = []

    def enqueue(self, repo_id):
        self.enqueued.append(repo_id)

    def enqueue_cleanup(self, repo_id, clone_path):
        self.cleanups.append((repo_id, clone_path))


def make_service():
    repos = FakeRepoRepo()
    dispatcher = FakeDispatcher()
    return RepositoryService(repositories=repos, dispatcher=dispatcher), repos, dispatcher


async def test_create_from_github_normalizes_and_dispatches():
    svc, repos, dispatcher = make_service()
    user_id = uuid.uuid4()
    repo = await svc.create_from_github(
        user_id=user_id, github_url="https://github.com/psf/requests.git", name=None
    )
    assert repo.github_url == "https://github.com/psf/requests"
    assert repo.name == "requests"
    assert repo.source is RepoSource.GITHUB
    assert dispatcher.enqueued == [repo.id]


async def test_create_from_github_rejects_invalid_url():
    svc, _, _ = make_service()
    with pytest.raises(ValueError):
        await svc.create_from_github(
            user_id=uuid.uuid4(), github_url="https://evil.com/x/y", name=None
        )


async def test_create_from_github_rejects_duplicate():
    svc, _, _ = make_service()
    user_id = uuid.uuid4()
    await svc.create_from_github(user_id=user_id, github_url="https://github.com/a/b", name=None)
    with pytest.raises(AlreadyExistsError):
        await svc.create_from_github(user_id=user_id, github_url="https://github.com/a/b", name=None)


async def test_get_is_owner_scoped():
    svc, repos, _ = make_service()
    owner = uuid.uuid4()
    other = uuid.uuid4()
    repo = await svc.create_from_github(user_id=owner, github_url="https://github.com/a/b", name=None)
    # Owner can read it; a different user cannot.
    assert (await svc.get(user_id=owner, repo_id=repo.id)).id == repo.id
    with pytest.raises(NotFoundError):
        await svc.get(user_id=other, repo_id=repo.id)


async def test_delete_enqueues_cleanup_and_is_owner_scoped():
    svc, repos, dispatcher = make_service()
    owner = uuid.uuid4()
    repo = await svc.create_from_github(user_id=owner, github_url="https://github.com/a/b", name=None)
    repo.clone_path = "/data/repos/x"
    await svc.delete(user_id=owner, repo_id=repo.id)
    assert dispatcher.cleanups == [(repo.id, "/data/repos/x")]
    assert repo.id not in repos.items


async def test_reindex_rejects_when_in_progress():
    svc, repos, _ = make_service()
    owner = uuid.uuid4()
    repo = await svc.create_from_github(user_id=owner, github_url="https://github.com/a/b", name=None)
    repos.items[repo.id].status = RepoStatus.INDEXING
    with pytest.raises(ValidationError):
        await svc.reindex(user_id=owner, repo_id=repo.id)

"""Unit test for the IndexingService pipeline using fakes + a temp working tree."""
from __future__ import annotations

import uuid
from pathlib import Path

from app.application.use_cases.repositories.indexing import IndexingService
from app.domain.entities.repository import Repository
from app.domain.enums import RepoSource, RepoStatus


class FakeRepoRepo:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self.statuses: list[RepoStatus] = []

    async def get(self, repo_id):
        return self._repo

    async def update(self, repository):
        self._repo = repository
        return repository

    async def update_status(self, repo_id, status, *, error_message=None):
        self.statuses.append(status)
        self._repo.status = status


class FakeMeta:
    def __init__(self) -> None:
        self.added: list[str] = []
        self.deleted = 0

    async def bulk_add(self, repo_id, chunks, chroma_ids):
        self.added.extend(chroma_ids)

    async def delete_for_repository(self, repo_id):
        self.deleted += 1

    async def count_for_repository(self, repo_id):
        return len(self.added)


class FakeEmbedder:
    async def embed(self, texts):
        return [[float(len(t)), 1.0, 2.0] for t in texts]

    async def embed_query(self, text):
        return [float(len(text)), 1.0, 2.0]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserts: list[int] = []
        self.deleted = 0

    async def upsert(self, *, repo_id, user_id, ids, embeddings, documents, metadatas):
        assert len(ids) == len(embeddings) == len(documents) == len(metadatas)
        # Isolation invariant: every chunk carries the owner + repo namespace.
        assert all(m["user_id"] == str(user_id) for m in metadatas)
        assert all(m["repo_id"] == str(repo_id) for m in metadatas)
        self.upserts.append(len(ids))

    async def query(self, *, repo_id, user_id, embedding, k):
        return []

    async def delete_repository(self, *, repo_id):
        self.deleted += 1


class FakeGit:
    async def clone(self, *, github_url, dest_dir):  # not used for upload source
        raise AssertionError("clone should not be called for upload repos")

    async def remove(self, clone_path):
        pass


async def test_indexing_pipeline_indexes_upload_and_marks_ready(tmp_path: Path):
    # Arrange a small working tree.
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "main.py").write_text("\n".join(f"x = {i}" for i in range(120)))
    (tmp_path / "README.md").write_text("# Title\n\nSome docs.\n")

    repo = Repository(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="demo",
        source=RepoSource.UPLOAD,
        status=RepoStatus.PENDING,
        clone_path=str(tmp_path),
    )
    repos = FakeRepoRepo(repo)
    meta = FakeMeta()
    vectors = FakeVectorStore()

    service = IndexingService(
        repositories=repos,
        embeddings_meta=meta,
        git=FakeGit(),
        embedder=FakeEmbedder(),
        vector_store=vectors,
        clone_root=str(tmp_path),
    )

    # Act
    await service.run(repo.id)

    # Assert: status ended READY, vectors + metadata written, prior data cleared.
    assert repo.status is RepoStatus.READY
    assert repo.indexed_at is not None
    assert vectors.deleted == 1  # idempotent clear before reindex
    assert meta.deleted == 1
    assert sum(vectors.upserts) == len(meta.added) > 0

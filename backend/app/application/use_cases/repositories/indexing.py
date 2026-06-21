"""Repository indexing pipeline (RAG ingestion).

Orchestrates: clone (GitHub only) → walk files → chunk → embed → store vectors →
persist embedding metadata → mark ready. Drives status transitions and records a
failure message on any error. Runs inside the Celery worker.
"""
from __future__ import annotations

import uuid

from app.application.interfaces.git import GitPort
from app.application.interfaces.repositories import (
    EmbeddingsMetadataRepository,
    RepositoryRepository,
    SymbolRepository,
)
from app.application.interfaces.vector import Chunk, EmbedderPort, VectorStorePort
from app.application.services.ast_index import extract_repository_symbols
from app.application.services.chunking import chunk_text
from app.application.services.repo_walker import walk_source_files
from app.core.logging import get_logger
from app.domain.enums import RepoSource, RepoStatus
from app.domain.exceptions import NotFoundError

logger = get_logger("indexing")

EMBED_BATCH_SIZE = 128


class IndexingService:
    def __init__(
        self,
        *,
        repositories: RepositoryRepository,
        embeddings_meta: EmbeddingsMetadataRepository,
        git: GitPort,
        embedder: EmbedderPort,
        vector_store: VectorStorePort,
        clone_root: str,
        symbols: SymbolRepository | None = None,
    ) -> None:
        self._repos = repositories
        self._meta = embeddings_meta
        self._git = git
        self._embedder = embedder
        self._vectors = vector_store
        self._clone_root = clone_root
        self._symbols = symbols

    async def run(self, repo_id: uuid.UUID) -> None:
        repo = await self._repos.get(repo_id)
        if repo is None:
            raise NotFoundError("Repository not found for indexing.")

        try:
            if repo.source is RepoSource.GITHUB:
                await self._repos.update_status(repo_id, RepoStatus.CLONING)
                dest = f"{self._clone_root}/{repo_id}"
                assert repo.github_url is not None
                clone = await self._git.clone(github_url=repo.github_url, dest_dir=dest)
                repo.clone_path = clone.clone_path
                repo.default_branch = clone.default_branch
                repo.commit_sha = clone.commit_sha
                repo.file_count = clone.file_count
                repo.total_lines = clone.total_lines
                repo.size_bytes = clone.size_bytes
                repo.primary_language = clone.primary_language
                repo.languages = clone.languages
                await self._repos.update(repo)

            if not repo.clone_path:
                raise NotFoundError("No working tree available to index.")

            await self._repos.update_status(repo_id, RepoStatus.INDEXING)

            # Fresh index: clear any previous vectors/metadata for idempotency.
            await self._vectors.delete_repository(repo_id=repo_id)
            await self._meta.delete_for_repository(repo_id)
            if self._symbols is not None:
                await self._symbols.delete_for_repository(repo_id)

            await self._index_symbols(repo_id, repo.clone_path)
            total_chunks = await self._index_working_tree(repo_id, repo.user_id, repo.clone_path)

            repo.status = RepoStatus.READY
            from datetime import UTC, datetime

            repo.indexed_at = datetime.now(UTC)
            await self._repos.update(repo)
            logger.info("index_complete", repo_id=str(repo_id), chunks=total_chunks)

        except Exception as exc:  # noqa: BLE001 - record and re-raise for worker retry
            logger.exception("index_failed", repo_id=str(repo_id))
            await self._repos.update_status(
                repo_id, RepoStatus.FAILED, error_message=str(exc)[:500]
            )
            raise

    async def _index_symbols(self, repo_id: uuid.UUID, clone_path: str) -> None:
        if self._symbols is None:
            return
        symbols = extract_repository_symbols(clone_path, repo_id)
        await self._symbols.bulk_add(symbols)
        logger.info("symbols_indexed", repo_id=str(repo_id), count=len(symbols))

    async def _index_working_tree(
        self, repo_id: uuid.UUID, user_id: uuid.UUID, clone_path: str
    ) -> int:
        batch: list[Chunk] = []
        total = 0
        for source in walk_source_files(clone_path):
            chunks = chunk_text(
                file_path=source.relative_path,
                content=source.content,
                language=source.language,
            )
            for chunk in chunks:
                batch.append(chunk)
                if len(batch) >= EMBED_BATCH_SIZE:
                    await self._flush(repo_id, user_id, batch)
                    total += len(batch)
                    batch = []
        if batch:
            await self._flush(repo_id, user_id, batch)
            total += len(batch)
        return total

    async def _flush(
        self, repo_id: uuid.UUID, user_id: uuid.UUID, batch: list[Chunk]
    ) -> None:
        embeddings = await self._embedder.embed([c.content for c in batch])
        chroma_ids = [f"{repo_id}:{c.file_path}:{c.chunk_index}" for c in batch]
        metadatas = [
            {
                "repo_id": str(repo_id),
                "user_id": str(user_id),
                "file_path": c.file_path,
                "language": c.language or "",
                "start_line": c.start_line,
                "end_line": c.end_line,
            }
            for c in batch
        ]
        await self._vectors.upsert(
            repo_id=repo_id,
            user_id=user_id,
            ids=chroma_ids,
            embeddings=embeddings,
            documents=[c.content for c in batch],
            metadatas=metadatas,
        )
        await self._meta.bulk_add(repo_id, batch, chroma_ids)

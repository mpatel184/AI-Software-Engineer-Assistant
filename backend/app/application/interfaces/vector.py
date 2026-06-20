"""Ports for embeddings and the vector store, plus the shared Chunk type."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class Chunk:
    """A unit of repository text to embed and retrieve."""

    file_path: str
    language: str | None
    chunk_index: int
    start_line: int
    end_line: int
    content: str
    content_hash: str
    token_count: int


@dataclass(slots=True)
class RetrievedChunk:
    file_path: str
    start_line: int
    end_line: int
    content: str
    score: float


class EmbedderPort(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


class VectorStorePort(Protocol):
    async def upsert(
        self,
        *,
        repo_id: uuid.UUID,
        user_id: uuid.UUID,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None: ...

    async def query(
        self,
        *,
        repo_id: uuid.UUID,
        user_id: uuid.UUID,
        embedding: list[float],
        k: int,
    ) -> list[RetrievedChunk]: ...

    async def delete_repository(self, *, repo_id: uuid.UUID) -> None: ...

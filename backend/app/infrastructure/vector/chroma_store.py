"""VectorStorePort implementation backed by ChromaDB (HTTP client).

Every chunk is namespaced by repo_id and user_id in its metadata. Queries filter
on both, so a user can never retrieve another user's repository content — this is
the enforcement point for unauthorized-repository-access prevention in RAG.
"""
from __future__ import annotations

import asyncio
import uuid
from functools import lru_cache

from app.application.interfaces.vector import RetrievedChunk, VectorStorePort
from app.domain.exceptions import ValidationError

_COLLECTION = "repository_chunks"

_REINDEX_HINT = (
    "The vector store was built with a different embedding model (vector "
    "dimension mismatch). Re-index this repository, or reset the Chroma volume, "
    "after changing EMBEDDING_MODEL."
)


def _is_dimension_error(exc: Exception) -> bool:
    return "dimension" in str(exc).lower()


@lru_cache(maxsize=1)
def _client(host: str, port: int):
    import chromadb

    return chromadb.HttpClient(host=host, port=port)


class ChromaVectorStore(VectorStorePort):
    def __init__(self, *, host: str, port: int) -> None:
        self._host = host
        self._port = port

    def _collection(self):
        client = _client(self._host, self._port)
        return client.get_or_create_collection(
            name=_COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    async def upsert(
        self,
        *,
        repo_id: uuid.UUID,
        user_id: uuid.UUID,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        try:
            await asyncio.to_thread(
                lambda: self._collection().upsert(
                    ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
                )
            )
        except Exception as exc:  # noqa: BLE001
            if _is_dimension_error(exc):
                raise ValidationError(_REINDEX_HINT) from exc
            raise

    async def query(
        self,
        *,
        repo_id: uuid.UUID,
        user_id: uuid.UUID,
        embedding: list[float],
        k: int,
    ) -> list[RetrievedChunk]:
        try:
            result = await asyncio.to_thread(
                lambda: self._collection().query(
                    query_embeddings=[embedding],
                    n_results=k,
                    where={
                        "$and": [
                            {"repo_id": {"$eq": str(repo_id)}},
                            {"user_id": {"$eq": str(user_id)}},
                        ]
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            if _is_dimension_error(exc):
                raise ValidationError(_REINDEX_HINT) from exc
            raise
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for doc, meta, dist in zip(documents, metadatas, distances, strict=False):
            chunks.append(
                RetrievedChunk(
                    file_path=str(meta.get("file_path", "")),
                    start_line=int(meta.get("start_line", 0)),
                    end_line=int(meta.get("end_line", 0)),
                    content=doc,
                    score=1.0 - float(dist),  # cosine distance → similarity
                )
            )
        return chunks

    async def delete_repository(self, *, repo_id: uuid.UUID) -> None:
        await asyncio.to_thread(
            lambda: self._collection().delete(where={"repo_id": {"$eq": str(repo_id)}})
        )

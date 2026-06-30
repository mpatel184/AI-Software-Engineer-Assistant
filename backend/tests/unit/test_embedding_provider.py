"""Unit tests for embedding provider selection and vector compatibility."""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.config import Settings
from app.domain.exceptions import ValidationError
from app.infrastructure.vector.chroma_store import ChromaVectorStore
from app.infrastructure.vector.embedder import LocalEmbeddingProvider, build_embedder


def _settings(**overrides: object) -> Settings:
    values = {
        "database_url": "postgresql+asyncpg://postgres:postgres@localhost/test",
        "redis_url": "redis://localhost:6379/1",
        "jwt_secret_key": "test-secret-key-at-least-32-characters-long-xx",
        "llm_api_key": "fake-key",
        "debug": False,
        **overrides,
    }
    return Settings(_env_file=None, **values)


def test_build_local_embedder_uses_configured_normalization():
    settings = _settings(embedding_provider="local", local_embedding_normalize=False)

    embedder = build_embedder(settings)

    assert isinstance(embedder, LocalEmbeddingProvider)
    assert embedder._normalize_embeddings is False


class _DimensionMismatchCollection:
    def upsert(self, **_: object) -> None:
        raise ValueError("Collection expecting embedding with dimension of 768, got 384")

    def query(self, **_: object) -> None:
        raise ValueError("Collection expecting embedding with dimension of 768, got 384")


@pytest.mark.asyncio
async def test_chroma_upsert_dimension_mismatch_has_provider_switch_hint(monkeypatch):
    store = ChromaVectorStore(host="localhost", port=8000)
    monkeypatch.setattr(store, "_collection", lambda: _DimensionMismatchCollection())

    with pytest.raises(ValidationError) as exc_info:
        await store.upsert(
            repo_id=uuid4(),
            user_id=uuid4(),
            ids=["chunk-1"],
            embeddings=[[0.0] * 384],
            documents=["content"],
            metadatas=[{"file_path": "a.py"}],
        )

    message = exc_info.value.message
    assert "dimension mismatch" in message
    assert "EMBEDDING_PROVIDER" in message
    assert "384-dimensional" in message
    assert "768-dimensional" in message


@pytest.mark.asyncio
async def test_chroma_query_dimension_mismatch_has_provider_switch_hint(monkeypatch):
    store = ChromaVectorStore(host="localhost", port=8000)
    monkeypatch.setattr(store, "_collection", lambda: _DimensionMismatchCollection())

    with pytest.raises(ValidationError) as exc_info:
        await store.query(
            repo_id=uuid4(),
            user_id=uuid4(),
            embedding=[0.0] * 384,
            k=3,
        )

    assert "LOCAL_EMBEDDING_MODEL" in exc_info.value.message

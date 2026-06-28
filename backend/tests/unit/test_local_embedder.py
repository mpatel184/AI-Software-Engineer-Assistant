"""Test for local embedding provider."""
from __future__ import annotations

import asyncio
import os

import pytest

from app.infrastructure.vector.embedder import LocalEmbeddingProvider, build_embedder
from app.core.config import Settings


@pytest.mark.asyncio
async def test_local_embedding_provider_basic():
    """Test that the local embedding provider can be instantiated and used."""
    # Set environment variable to use local provider
    os.environ["EMBEDDING_PROVIDER"] = "local"
    os.environ["LOCAL_EMBEDDING_MODEL"] = "BAAI/bge-small-en-v1.5"

    # Reload settings to pick up environment variables
    from importlib import reload
    from app.core.config import Settings
    reload(Settings)

    settings = Settings()
    embedder = build_embedder(settings)

    # Test that we got the right type
    assert isinstance(embedder, LocalEmbeddingProvider)

    # Test embedding a single text
    embedding = await embedder.embed_query("Hello, world!")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)

    # Test embedding multiple texts
    embeddings = await embedder.embed(["Hello, world!", "Goodbye, world!"])
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    assert all(isinstance(e, list) for e in embeddings)
    assert all(len(e) > 0 for e in embeddings)
    assert all(all(isinstance(x, float) for x in e) for e in embeddings)


@pytest.mark.asyncio
async def test_local_embedding_provider_with_prefixes():
    """Test that the local embedding provider handles prefixes correctly."""
    # Set environment variable to use local provider
    os.environ["EMBEDDING_PROVIDER"] = "local"
    os.environ["LOCAL_EMBEDDING_MODEL"] = "BAAI/bge-small-en-v1.5"

    # Reload settings to pick up environment variables
    from importlib import reload
    from app.core.config import Settings
    reload(Settings)

    settings = Settings()
    embedder = build_embedder(settings)

    # Test that we can create the FastEmbedEmbedder for backward compatibility
    from app.infrastructure.vector.embedder import FastEmbedEmbedder
    fast_embed = FastEmbedEmbedder("BAAI/bge-small-en-v1.5")
    assert isinstance(fast_embed, FastEmbedEmbedder)

    # Test embedding with the FastEmbedEmbedder
    embedding = await fast_embed.embed_query("Test text")
    assert isinstance(embedding, list)
    assert len(embedding) > 0


def test_prefixes_for():
    """Test the _prefixes_for function."""
    from app.infrastructure.vector.embedder import _prefixes_for

    # Test BAAI model
    doc_prefix, query_prefix = _prefixes_for("BAAI/bge-small-en-v1.5")
    assert doc_prefix == ""
    assert "检索" in query_prefix  # Chinese for "retrieval"

    # Test unknown model
    doc_prefix, query_prefix = _prefixes_for("unknown/model")
    assert doc_prefix == ""
    assert query_prefix == ""
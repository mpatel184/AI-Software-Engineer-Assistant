"""Unit tests for embedding task-prefix resolution (no model download)."""
from __future__ import annotations

from app.infrastructure.vector.embedder import FastEmbedEmbedder, _prefixes_for


def test_nomic_prefixes():
    doc, query = _prefixes_for("nomic-ai/nomic-embed-text-v1.5")
    assert doc == "search_document: "
    assert query == "search_query: "


def test_bge_query_prefix_only():
    doc, query = _prefixes_for("BAAI/bge-small-en-v1.5")
    assert doc == ""
    assert "searching relevant passages" in query


def test_unknown_model_has_no_prefixes():
    assert _prefixes_for("some/other-model") == ("", "")


def test_embedder_stores_prefixes():
    emb = FastEmbedEmbedder("nomic-ai/nomic-embed-text-v1.5", doc_prefix="d: ", query_prefix="q: ")
    assert emb._doc_prefix == "d: "
    assert emb._query_prefix == "q: "

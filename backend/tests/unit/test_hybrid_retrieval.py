"""Unit tests for the hybrid retriever (vector + symbol fusion)."""
from __future__ import annotations

import uuid

from app.application.services.hybrid_retrieval import HybridRetriever, _keywords
from app.application.interfaces.vector import RetrievedChunk
from app.domain.entities.symbol import Symbol
from app.domain.enums import SymbolKind


class FakeEmbedder:
    async def embed(self, texts):
        return [[0.0] for _ in texts]

    async def embed_query(self, text):
        return [0.0]


class FakeVectors:
    def __init__(self, chunks):
        self.chunks = chunks

    async def query(self, *, repo_id, user_id, embedding, k):
        return self.chunks[:k]


class FakeSymbols:
    def __init__(self, symbols):
        self.symbols = symbols
        self.last_kinds = None

    async def search(self, repo_id, query, *, kinds=None, limit=10):
        self.last_kinds = kinds
        return [s for s in self.symbols if query.lower() in s.name.lower()][:limit]


def _sym(name, kind=SymbolKind.FUNCTION, file="a.py", line=10):
    return Symbol(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        file_path=file,
        kind=kind,
        name=name,
        qualified_name=name,
        signature=f"def {name}()",
        start_line=line,
        end_line=line + 2,
    )


def test_keywords_drops_stopwords_and_short_tokens():
    kw = _keywords("How does the validateToken function work?")
    assert "validateToken" in kw
    assert "does" not in kw and "the" not in kw


async def test_symbol_hits_rank_before_vector_hits():
    vectors = FakeVectors([RetrievedChunk("z.py", 1, 5, "semantic", 0.5)])
    symbols = FakeSymbols([_sym("validateToken")])
    r = HybridRetriever(embedder=FakeEmbedder(), vectors=vectors, symbols=symbols)

    out = await r.retrieve(
        repo_id=uuid.uuid4(), user_id=uuid.uuid4(), query="where is validateToken", k=5
    )
    assert out[0].file_path == "a.py"  # symbol hit first
    assert any(c.file_path == "z.py" for c in out)  # vector hit included


async def test_endpoint_question_filters_route_symbols():
    symbols = FakeSymbols([_sym("users", kind=SymbolKind.ROUTE)])
    r = HybridRetriever(embedder=FakeEmbedder(), vectors=FakeVectors([]), symbols=symbols)
    await r.retrieve(
        repo_id=uuid.uuid4(), user_id=uuid.uuid4(), query="list all api endpoints for users", k=5
    )
    assert symbols.last_kinds == [SymbolKind.ROUTE]


async def test_dedupes_identical_locations():
    dup = RetrievedChunk("a.py", 10, 12, "x", 0.9)
    vectors = FakeVectors([dup])
    symbols = FakeSymbols([_sym("foo", line=10)])  # same file+lines as dup
    r = HybridRetriever(embedder=FakeEmbedder(), vectors=vectors, symbols=symbols)
    out = await r.retrieve(repo_id=uuid.uuid4(), user_id=uuid.uuid4(), query="foo", k=5)
    locations = [(c.file_path, c.start_line, c.end_line) for c in out]
    assert len(locations) == len(set(locations))

"""Hybrid retriever: semantic vectors + exact symbol lookup + AST signatures.

Combines three signals so the assistant answers both fuzzy ("how does auth
work?") and precise ("where is JWT validated?", "find all API endpoints")
questions:

1. Vector search over embedded code chunks (semantic recall).
2. Symbol-index lookup on identifiers in the question (exact precision); for
   endpoint-style questions, ROUTE symbols are prioritized.
3. Symbol hits are surfaced as excerpts carrying their signature + docstring.

Symbol matches are ranked ahead of vector hits, then merged and de-duplicated.
"""
from __future__ import annotations

import re
import uuid

from app.application.interfaces.repositories import SymbolRepository
from app.application.interfaces.vector import (
    EmbedderPort,
    RetrievedChunk,
    VectorStorePort,
)
from app.domain.entities.symbol import Symbol
from app.domain.enums import SymbolKind

_STOPWORDS = {
    "the", "and", "for", "are", "how", "does", "what", "where", "which", "with",
    "this", "that", "from", "into", "you", "your", "can", "all", "find", "show",
    "explain", "list", "get", "use", "used", "uses", "code", "repo", "repository",
    "function", "functions", "class", "classes", "method", "file", "files", "is",
    "in", "of", "to", "a", "an", "do", "i", "me", "it",
}
_ROUTE_HINTS = {"endpoint", "endpoints", "route", "routes", "api", "url", "path"}
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def _keywords(question: str) -> list[str]:
    seen: list[str] = []
    for tok in _IDENT.findall(question):
        low = tok.lower()
        if low in _STOPWORDS or low in _ROUTE_HINTS:
            continue
        if tok not in seen:
            seen.append(tok)
    return seen[:5]


def _symbol_to_chunk(s: Symbol) -> RetrievedChunk:
    body = s.signature
    if s.docstring:
        body += f"\n{s.docstring.strip()}"
    return RetrievedChunk(
        file_path=s.file_path,
        start_line=s.start_line,
        end_line=s.end_line,
        content=body,
        score=0.95,  # exact symbol match ranks high
    )


class HybridRetriever:
    def __init__(
        self,
        *,
        embedder: EmbedderPort,
        vectors: VectorStorePort,
        symbols: SymbolRepository,
        max_symbol_hits: int = 3,
    ) -> None:
        self._embedder = embedder
        self._vectors = vectors
        self._symbols = symbols
        self._max_symbol_hits = max_symbol_hits

    async def _symbol_hits(self, repo_id: uuid.UUID, question: str) -> list[RetrievedChunk]:
        kinds = [SymbolKind.ROUTE] if self._wants_routes(question) else None
        hits: list[RetrievedChunk] = []
        seen: set[tuple[str, int]] = set()
        for term in _keywords(question):
            for sym in await self._symbols.search(repo_id, term, kinds=kinds, limit=5):
                key = (sym.file_path, sym.start_line)
                if key in seen:
                    continue
                seen.add(key)
                hits.append(_symbol_to_chunk(sym))
                if len(hits) >= self._max_symbol_hits:
                    return hits
        return hits

    @staticmethod
    def _wants_routes(question: str) -> bool:
        words = {w.lower() for w in _IDENT.findall(question)}
        return bool(words & _ROUTE_HINTS)

    async def retrieve(
        self,
        *,
        repo_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        k: int,
    ) -> list[RetrievedChunk]:
        embedding = await self._embedder.embed_query(query)
        vector_hits = await self._vectors.query(
            repo_id=repo_id, user_id=user_id, embedding=embedding, k=k
        )
        symbol_hits = await self._symbol_hits(repo_id, query)

        merged: list[RetrievedChunk] = []
        seen: set[tuple[str, int, int]] = set()
        for chunk in [*symbol_hits, *vector_hits]:
            key = (chunk.file_path, chunk.start_line, chunk.end_line)
            if key in seen:
                continue
            seen.add(key)
            merged.append(chunk)
        return merged[: k + self._max_symbol_hits]

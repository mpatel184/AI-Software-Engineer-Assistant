"""EmbedderPort implementation backed by a local fastembed model.

The model is loaded lazily on first use (it downloads weights once) and reused.
Embedding runs in a thread to avoid blocking the event loop.

Some models require task-specific prefixes for good retrieval quality:
* nomic-embed-text → "search_document: " for passages, "search_query: " for queries
* bge-*            → a query-side instruction prefix

`build_embedder` resolves the right prefixes from the configured model name, so
callers never hard-code them.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache

from app.application.interfaces.vector import EmbedderPort
from app.core.config import Settings

# model-name substring -> (document_prefix, query_prefix)
_PREFIXES: dict[str, tuple[str, str]] = {
    "nomic-embed-text": ("search_document: ", "search_query: "),
    "bge-": ("", "Represent this sentence for searching relevant passages: "),
}


def _prefixes_for(model_name: str) -> tuple[str, str]:
    lower = model_name.lower()
    for key, prefixes in _PREFIXES.items():
        if key in lower:
            return prefixes
    return ("", "")


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    # Imported lazily so importing this module is cheap and import-safe.
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


class FastEmbedEmbedder(EmbedderPort):
    def __init__(
        self, model_name: str, *, doc_prefix: str = "", query_prefix: str = ""
    ) -> None:
        self._model_name = model_name
        self._doc_prefix = doc_prefix
        self._query_prefix = query_prefix

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        prefixed = [self._doc_prefix + t for t in texts]
        return await asyncio.to_thread(self._embed_sync, prefixed)

    async def embed_query(self, text: str) -> list[float]:
        result = await asyncio.to_thread(self._embed_sync, [self._query_prefix + text])
        return result[0]

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        model = _load_model(self._model_name)
        return [vector.tolist() for vector in model.embed(texts)]


def build_embedder(settings: Settings) -> EmbedderPort:
    """Construct the configured embedder with model-appropriate task prefixes."""
    doc_prefix, query_prefix = _prefixes_for(settings.embedding_model)
    return FastEmbedEmbedder(
        settings.embedding_model, doc_prefix=doc_prefix, query_prefix=query_prefix
    )

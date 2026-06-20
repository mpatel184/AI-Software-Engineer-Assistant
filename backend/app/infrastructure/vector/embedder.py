"""EmbedderPort implementation backed by a local fastembed model.

The model is loaded lazily on first use (it downloads weights once) and reused.
Embedding runs in a thread to avoid blocking the event loop.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache

from app.application.interfaces.vector import EmbedderPort


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    # Imported lazily so importing this module is cheap and import-safe.
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


class FastEmbedEmbedder(EmbedderPort):
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, texts)

    async def embed_query(self, text: str) -> list[float]:
        result = await asyncio.to_thread(self._embed_sync, [text])
        return result[0]

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        model = _load_model(self._model_name)
        return [vector.tolist() for vector in model.embed(texts)]

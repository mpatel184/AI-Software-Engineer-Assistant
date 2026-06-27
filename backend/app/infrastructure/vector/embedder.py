"""EmbedderPort implementation backed by any OpenAI-compatible /embeddings endpoint.

By default targets Google's ``text-embedding-004`` model via the Gemini API
(https://generativelanguage.googleapis.com/v1beta/openai). Any other
OpenAI-compatible embeddings endpoint can be used by changing EMBEDDING_MODEL
and EMBEDDING_API_KEY in the environment.

The HTTP call is made with httpx (already a project dependency) so no additional
packages are required.

Dimension note
--------------
``text-embedding-004`` returns 768-dimensional vectors — the same as the
previously used ``nomic-embed-text-v1.5``. Fresh ChromaDB collections will use
768 dimensions automatically. Existing collections built with a different model
will raise a dimension-mismatch ValidationError (handled by ChromaVectorStore);
a re-index is required in that case.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.application.interfaces.vector import EmbedderPort
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("embedder.openai_compat")

_RETRYABLE = (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)


class OpenAICompatEmbedder(EmbedderPort):
    """Embedder backed by any OpenAI-compatible /embeddings endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    # ------------------------------------------------------------------
    # EmbedderPort interface
    # ------------------------------------------------------------------

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, texts)

    async def embed_query(self, text: str) -> list[float]:
        results = await asyncio.to_thread(self._embed_sync, [text])
        return results[0]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous (blocking) call — runs in a thread pool via asyncio.to_thread."""
        return self._call_embeddings_api(texts)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_embeddings_api(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {"model": self._model, "input": texts}
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/embeddings", json=payload, headers=headers
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Embeddings API error {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        try:
            # OpenAI format: {"data": [{"embedding": [...], "index": N}, ...]}
            sorted_items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_items]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Malformed response from embeddings API.") from exc


def build_embedder(settings: Settings) -> EmbedderPort:
    """Construct the configured embedder from env settings."""
    return OpenAICompatEmbedder(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
    )

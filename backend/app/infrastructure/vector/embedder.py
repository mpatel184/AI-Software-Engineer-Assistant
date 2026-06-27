from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.application.interfaces.vector import EmbedderPort
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("embedder.openai_compat")

_RETRYABLE = (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)


class OpenAICompatEmbedder(EmbedderPort):
    """
    Embedder backed by any OpenAI-compatible /embeddings endpoint
    (Gemini, OpenAI, Azure, etc.)
    """

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

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, texts)

    async def embed_query(self, text: str) -> list[float]:
        results = await asyncio.to_thread(self._embed_sync, [text])
        return results[0]

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        return self._call_embeddings_api(texts)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_embeddings_api(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": self._model,
            "input": texts,
        }

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/embeddings",
                json=payload,
                headers=headers,
            )

        # ❗ hard failure on HTTP errors
        if response.status_code >= 400:
            raise RuntimeError(
                f"Embeddings API error {response.status_code}: {response.text[:500]}"
            )

        # Parse JSON safely
        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError(f"Invalid JSON response: {response.text[:500]}") from exc

        print("=" * 80)
        print("STATUS:", response.status_code)
        print("RAW RESPONSE:", response.text[:1000])
        print("=" * 80)

        # -------------------------------
        # SAFE extraction logic
        # -------------------------------
        items = data.get("data")

        if not isinstance(items, list) or len(items) == 0:
            raise RuntimeError(f"Unexpected embeddings format: {data}")

        embeddings: list[list[float]] = []

        for i, item in enumerate(items):
            if not isinstance(item, dict):
                raise RuntimeError(f"Invalid item format at index {i}: {item}")

            emb = item.get("embedding")

            # Case 1: normal list
            if isinstance(emb, list):
                embeddings.append(emb)

            # Case 2: nested Gemini-style object
            elif isinstance(emb, dict) and "values" in emb:
                embeddings.append(emb["values"])

            # Case 3: completely unexpected
            else:
                raise RuntimeError(f"Unknown embedding format at index {i}: {item}")

        if not embeddings:
            raise RuntimeError(f"No embeddings extracted: {data}")

        return embeddings


def build_embedder(settings: Settings) -> EmbedderPort:
    return OpenAICompatEmbedder(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
    )
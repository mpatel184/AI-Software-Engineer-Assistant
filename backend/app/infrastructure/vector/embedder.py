from __future__ import annotations

import asyncio
from typing import Any

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.application.interfaces.vector import EmbedderPort
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("embedder")

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
        def chunk(lst, size=100):
            for i in range(0, len(lst), size):
                yield lst[i:i + size]

        all_embeddings: list[list[float]] = []

        for batch in chunk(texts, 100):
            payload: dict[str, Any] = {
                "model": self._model,
                "input": batch,
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

            if response.status_code >= 400:
                raise RuntimeError(
                    f"Embeddings API error {response.status_code}: {response.text[:500]}"
                )

            data = response.json()

            items = data.get("data", [])
            for item in items:
                all_embeddings.append(item["embedding"])

        return all_embeddings


class LocalEmbeddingProvider(EmbedderPort):
    """
    Local embedding provider using sentence-transformers.

    Loads the model once and reuses it for all embedding calls.
    Thread-safe for concurrent access.
    """

    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str | None = None,
        normalize_embeddings: bool = True,
    ) -> None:
        """
        Initialize the local embedding provider.

        Args:
            model_name: Hugging Face model identifier
            device: Device to run model on ('cpu', 'cuda', etc.). If None, auto-detects.
            normalize_embeddings: Whether to L2-normalize embeddings
        """
        self._model_name = model_name
        self._normalize_embeddings = normalize_embeddings
        self._device = device
        self._model_lock = asyncio.Lock()
        self._model: SentenceTransformer | None = None

        logger.info(
            "local_embedding_provider.initializing",
            model_name=model_name,
            device=device or "auto",
            normalize=normalize_embeddings,
        )

    async def _load_model(self) -> SentenceTransformer:
        """Load the sentence-transformers model (async, thread-safe, lazy loading)."""
        if self._model is None:
            async with self._model_lock:
                if self._model is None:  # Double-check locking
                    logger.info(
                        "local_embedding_provider.loading_model",
                        model_name=self._model_name,
                        device=self._device or "auto",
                    )
                    # Load model in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(
                        None,
                        lambda: SentenceTransformer(
                            self._model_name,
                            device=self._device,
                        ),
                    )
                    logger.info(
                        "local_embedding_provider.model_loaded",
                        model_name=self._model_name,
                        embedding_dim=self._model.get_embedding_dimension(),
                    )
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts using the local sentence-transformers model.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each as list of floats)
        """
        if not texts:
            return []

        model = await self._load_model()
        # Run embedding in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(
                texts,
                normalize_embeddings=self._normalize_embeddings,
                convert_to_numpy=True,
                show_progress_bar=False,
            ),
        )

        # Convert numpy arrays to lists of floats
        if isinstance(embeddings, np.ndarray):
            embeddings = embeddings.tolist()

        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        """
        Embed a single query text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as list of floats
        """
        embeddings = await self.embed([text])
        return embeddings[0]


def build_embedder(settings: Settings) -> EmbedderPort:
    """
    Build an embedder instance based on configuration.

    Returns:
        EmbedderPort implementation (local or remote)
    """
    if settings.embedding_provider == "local":
        logger.info(
            "embedder.creating_local",
            model_name=settings.local_embedding_model,
            device=settings.local_embedding_device or "auto",
        )
        return LocalEmbeddingProvider(
            model_name=settings.local_embedding_model,
            device=settings.local_embedding_device,
            normalize_embeddings=settings.local_embedding_normalize,
        )
    else:
        # Default to OpenAI-compatible provider (Gemini, OpenAI, etc.)
        logger.info(
            "embedder.creating_openai_compat",
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
        )
        return OpenAICompatEmbedder(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
        )

"""Local embedding provider using sentence-transformers."""
from __future__ import annotations

import threading
from typing import Any, List

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from app.application.interfaces.vector import EmbedderPort
from app.core.logging import get_logger

logger = get_logger("embedder.local")


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
        self._model_lock = threading.Lock()
        self._model: SentenceTransformer | None = None

        logger.info(
            "local_embedding_provider.initializing",
            model_name=model_name,
            device=device or "auto",
            normalize=normalize_embeddings,
        )

    def _load_model(self) -> SentenceTransformer:
        """Load the sentence-transformers model (thread-safe, lazy loading)."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:  # Double-check locking
                    logger.info(
                        "local_embedding_provider.loading_model",
                        model_name=self._model_name,
                        device=self._device or "auto",
                    )
                    try:
                        self._model = SentenceTransformer(
                            self._model_name,
                            device=self._device,
                        )
                        logger.info(
                            "local_embedding_provider.model_loaded",
                            model_name=self._model_name,
                            embedding_dim=self._model.get_sentence_embedding_dimension(),
                        )
                    except Exception as e:
                        logger.error(
                            "local_embedding_provider.model_load_failed",
                            model_name=self._model_name,
                            error=str(e),
                            exc_info=True,
                        )
                        raise
        return self._model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts using the local sentence-transformers model.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each as list of floats)
        """
        if not texts:
            return []

        # Run embedding in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, self._sync_embed, texts
        )
        return embeddings

    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as list of floats
        """
        embeddings = await self.embed([text])
        return embeddings[0]

    def _sync_embed(self, texts: List[str]) -> List[List[float]]:
        """Synchronous embedding computation."""
        model = self._load_model()

        # Encode embeddings
        embeddings = model.encode(
            texts,
            normalize_embeddings=self._normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        # Convert numpy arrays to lists of floats
        if isinstance(embeddings, np.ndarray):
            embeddings = embeddings.tolist()

        return embeddings


import asyncio  # Imported here to avoid circular imports during type checking
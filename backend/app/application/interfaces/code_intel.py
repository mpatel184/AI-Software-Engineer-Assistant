"""Ports for code-intelligence retrieval (RAG + symbol + AST fusion)."""
from __future__ import annotations

import uuid
from typing import Protocol

from app.application.interfaces.vector import RetrievedChunk


class RetrieverPort(Protocol):
    async def retrieve(
        self,
        *,
        repo_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        k: int,
    ) -> list[RetrievedChunk]:
        """Return the most relevant repository excerpts for a query."""

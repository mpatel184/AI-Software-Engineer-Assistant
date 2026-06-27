"""Placeholder Claude provider — not yet implemented.

To use an LLM right now, set LLM_PROVIDER=openai (works with Gemini, Z.ai,
OpenAI, or any OpenAI-compatible endpoint). See backend/.env.example.
"""
from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.llm.base import LLMProvider


class FutureClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, settings: Settings) -> None:  # noqa: ARG002
        raise NotImplementedError(
            "ClaudeProvider is not yet implemented. "
            "Set LLM_PROVIDER=openai to use any OpenAI-compatible API "
            "(e.g. Gemini, Z.ai GLM). See backend/.env.example."
        )

    async def complete(self, *, system: str, user: str, max_tokens: int | None = None) -> str:
        raise NotImplementedError

    async def complete_json(
        self, *, system: str, user: str, schema: dict, max_tokens: int | None = None
    ) -> dict:
        raise NotImplementedError

"""Placeholder OpenAI provider.

Not implemented — the project runs entirely on local models. This stub exists so
the provider hierarchy is complete and a future hosted backend can be added
without touching the application layer.
"""
from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.llm.base import LLMProvider


class FutureOpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:  # noqa: ARG002
        raise NotImplementedError(
            "OpenAIProvider is not implemented. Set LLM_PROVIDER=qwen to use the "
            "local Qwen3-Coder backend."
        )

    async def complete(self, *, system: str, user: str, max_tokens: int | None = None) -> str:
        raise NotImplementedError

    async def complete_json(
        self, *, system: str, user: str, schema: dict, max_tokens: int | None = None
    ) -> dict:
        raise NotImplementedError

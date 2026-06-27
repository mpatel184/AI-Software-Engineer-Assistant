"""Model-agnostic LLM provider abstraction.

`LLMProvider` is the abstract base that every concrete provider implements. It
structurally satisfies the application-layer ``LLMPort`` protocol, so use-cases
depend only on the port and never on a concrete provider or backend.

Provider hierarchy:
    LLMProvider (ABC)
     ├── OpenAICompatProvider   (default — any OpenAI-compatible API, e.g. Gemini, Z.ai)
     ├── GeminiProvider         (alias of OpenAICompatProvider with name="gemini")
     ├── QwenProvider           (backward-compat for local self-hosted setups)
     └── FutureClaudeProvider   (stub)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import Settings


class LLMProvider(ABC):
    """Abstract LLM provider. Implementations must be fully async."""

    name: str = "abstract"

    def __init__(self, settings: Settings) -> None:  # noqa: ARG002
        """Initialise the provider with application settings."""
        super().__init__()

    @abstractmethod
    async def complete(
        self, *, system: str, user: str, max_tokens: int | None = None
    ) -> str:
        """Return a plain-text completion."""
        raise NotImplementedError

    @abstractmethod
    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int | None = None,
    ) -> dict:
        """Return a JSON object constrained to the given JSON schema."""
        raise NotImplementedError

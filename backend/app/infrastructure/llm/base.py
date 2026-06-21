"""Model-agnostic LLM provider abstraction.

`LLMProvider` is the abstract base that every concrete provider implements. It
structurally satisfies the application-layer ``LLMPort`` protocol, so use-cases
depend only on the port and never on a concrete provider or backend.

Provider hierarchy:
    LLMProvider (ABC)
     ├── QwenProvider          (implemented — local, OpenAI-compatible)
     ├── FutureOpenAIProvider  (stub)
     ├── FutureClaudeProvider  (stub)
     └── FutureGeminiProvider  (stub)
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract LLM provider. Implementations must be fully async."""

    name: str = "abstract"

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

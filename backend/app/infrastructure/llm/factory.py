"""Factory selecting the configured LLM provider (composition root for the AI layer).

The default provider is ``openai`` (OpenAICompatProvider) which works with any
OpenAI-compatible endpoint — set LLM_BASE_URL + LLM_API_KEY + LLM_MODEL in the
environment. See backend/.env.example for Gemini and Z.ai examples.
"""
from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.llm.base import LLMProvider
from app.infrastructure.llm.providers.future_claude_provider import FutureClaudeProvider
from app.infrastructure.llm.providers.future_gemini_provider import GeminiProvider
from app.infrastructure.llm.providers.future_openai_provider import OpenAICompatProvider
from app.infrastructure.llm.providers.qwen_provider import QwenProvider

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAICompatProvider,
    "gemini": GeminiProvider,
    "qwen": QwenProvider,
    "claude": FutureClaudeProvider,
}


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Instantiate the provider named by ``settings.llm_provider``."""
    try:
        provider_cls = _PROVIDERS[settings.llm_provider]
    except KeyError as exc:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}") from exc
    return provider_cls(settings)

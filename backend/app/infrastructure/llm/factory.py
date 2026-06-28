"""Factory that builds a ProviderManager from application settings.

This is the *only* place where provider names are resolved to concrete classes.
The rest of the application receives a ``ProviderManager`` (which satisfies both
``LLMProvider`` ABC and ``LLMPort`` Protocol) and never knows which provider
is active.

Supported primary providers
---------------------------
* ``gemini``  — Gemini 2.5 Flash via Google AI Studio (default)
* ``openai``  — Any OpenAI-compatible endpoint
* ``qwen``    — Local Qwen (legacy; kept for backward compat)

Supported fallback providers
-----------------------------
* ``glm``     — Z.ai GLM via open.bigmodel.cn
* ``none``    — Fallback disabled (default)

Adding a new provider
---------------------
1. Create ``app/infrastructure/llm/providers/my_provider.py`` with a class
   that extends ``LLMProvider``.
2. Add it to ``_PRIMARY_PROVIDERS`` or ``_FALLBACK_PROVIDERS`` below.
3. Add the new name to the ``Literal`` in ``Settings`` (``core/config.py``).
That's it — no other code changes required.
"""
from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.exceptions import ConfigurationError
from app.infrastructure.llm.base import LLMProvider
from app.infrastructure.llm.manager import ProviderManager
from app.infrastructure.llm.providers.future_claude_provider import FutureClaudeProvider
from app.infrastructure.llm.providers.future_gemini_provider import GeminiProvider
from app.infrastructure.llm.providers.future_openai_provider import OpenAICompatProvider
from app.infrastructure.llm.providers.glm_provider import GLMProvider
from app.infrastructure.llm.providers.qwen_provider import QwenProvider

logger = get_logger("llm.factory")

_PRIMARY_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAICompatProvider,
    "gemini": GeminiProvider,
    "qwen": QwenProvider,
    "claude": FutureClaudeProvider,
}

_FALLBACK_PROVIDERS: dict[str, type[LLMProvider]] = {
    "glm": GLMProvider,
    # Future additions: "openai": OpenAICompatProvider, "groq": GroqProvider, ...
}


def _build_primary(settings: Settings) -> LLMProvider:
    provider_name = settings.llm_provider
    cls = _PRIMARY_PROVIDERS.get(provider_name)
    if cls is None:
        raise ConfigurationError(
            f"Unknown LLM_PROVIDER={provider_name!r}. "
            f"Valid options: {list(_PRIMARY_PROVIDERS)}"
        )
    logger.info("llm_primary_provider_loaded", provider=provider_name)
    return cls(settings)


def _build_fallback(settings: Settings) -> LLMProvider | None:
    fallback_name = settings.fallback_provider
    if fallback_name == "none":
        return None

    cls = _FALLBACK_PROVIDERS.get(fallback_name)
    if cls is None:
        raise ConfigurationError(
            f"Unknown FALLBACK_PROVIDER={fallback_name!r}. "
            f"Valid options: {list(_FALLBACK_PROVIDERS)} or 'none'."
        )

    if fallback_name == "glm" and not settings.glm_api_key:
        raise ConfigurationError(
            "FALLBACK_PROVIDER=glm requires GLM_API_KEY to be set."
        )

    logger.info("llm_fallback_provider_loaded", provider=fallback_name)
    return cls(settings)


def get_llm_provider(settings: Settings) -> ProviderManager:
    """Build and return the ProviderManager configured by environment variables.

    Returns a ProviderManager regardless of provider config — callers never
    interact with concrete providers directly.
    """
    primary = _build_primary(settings)
    fallback = _build_fallback(settings)

    manager = ProviderManager(
        primary=primary,
        fallback=fallback,
        max_retries=settings.llm_max_retries,
        retry_backoff=settings.llm_retry_backoff,
    )

    if fallback is not None:
        logger.info(
            "llm_manager_ready",
            primary=primary.name,
            fallback=fallback.name,
            max_retries=settings.llm_max_retries,
            retry_backoff=settings.llm_retry_backoff,
        )
    else:
        logger.info(
            "llm_manager_ready",
            primary=primary.name,
            fallback="none",
            max_retries=settings.llm_max_retries,
        )

    return manager
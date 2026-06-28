"""ProviderManager: centralized retry and fallback orchestrator for LLM calls.

The rest of the application (use-cases, workers, deps) always receives a
ProviderManager as the ``LLMPort`` implementation.  No provider-specific code
ever leaks beyond this module.

Retry/fallback strategy
-----------------------
1. Call primary provider.
2. On a *retryable* failure: wait ``backoff * 2^attempt`` seconds and retry
   (up to ``max_retries`` attempts).
3. If all primary retries are exhausted *and* a fallback provider is configured:
   switch to the fallback and attempt it once.
4. If the fallback also fails, raise ``ProviderUnavailableError``.

Non-retryable failures (auth errors, invalid requests, safety blocks) are
re-raised immediately without switching providers.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.logging import get_logger
from app.domain.exceptions import (
    ExternalServiceError,
    ProviderAuthenticationError,
    ProviderUnavailableError,
    RetryableProviderError,
)
from app.infrastructure.llm.base import LLMProvider

logger = get_logger("llm.manager")

# Exceptions that are always retryable regardless of provider.
_RETRYABLE_HTTPX = (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)

# ExternalServiceError messages produced by OpenAICompatibleClient for 429/5xx.
_RETRYABLE_MSG_FRAGMENTS = ("rate limit", "server error", "timed out", "connection")


def _is_retryable(exc: BaseException) -> bool:
    """Return True if `exc` should trigger a retry or fallback."""
    if isinstance(exc, _RETRYABLE_HTTPX):
        return True
    if isinstance(exc, RetryableProviderError):
        return True
    if isinstance(exc, ExternalServiceError):
        msg = str(exc).lower()
        return any(frag in msg for frag in _RETRYABLE_MSG_FRAGMENTS)
    return False


def _is_auth_error(exc: BaseException) -> bool:
    """Return True if `exc` indicates a bad API key or auth failure.

    These must NOT trigger fallback — the configuration needs to be fixed.
    """
    if isinstance(exc, ProviderAuthenticationError):
        return True
    if isinstance(exc, ExternalServiceError):
        msg = str(exc).lower()
        return any(
            frag in msg
            for frag in ("401", "403", "unauthorized", "forbidden", "api key", "authentication")
        )
    return False


class ProviderManager(LLMProvider):
    """Orchestrates primary → fallback provider selection with retries.

    Satisfies the ``LLMProvider`` ABC and the ``LLMPort`` Protocol, so it
    drops in wherever either is expected.
    """

    name = "manager"

    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider | None,
        *,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff

    # ------------------------------------------------------------------
    # Public interface — satisfies LLMProvider / LLMPort
    # ------------------------------------------------------------------

    async def complete(
        self, *, system: str, user: str, max_tokens: int | None = None
    ) -> str:
        kwargs: dict[str, Any] = {"system": system, "user": user, "max_tokens": max_tokens}
        return await self._execute("complete", **kwargs)

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int | None = None,
    ) -> dict:
        kwargs: dict[str, Any] = {
            "system": system,
            "user": user,
            "schema": schema,
            "max_tokens": max_tokens,
        }
        return await self._execute("complete_json", **kwargs)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------

    async def _execute(self, method: str, **kwargs: Any) -> Any:
        """Run `method` on primary with retries, then on fallback if configured."""
        last_exc: BaseException | None = None

        # --- Primary provider with exponential-backoff retries ---
        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    "llm_provider_attempt",
                    provider=self._primary.name,
                    method=method,
                    attempt=attempt,
                )
                result = await getattr(self._primary, method)(**kwargs)
                if attempt > 1:
                    logger.info(
                        "llm_provider_recovered",
                        provider=self._primary.name,
                        attempt=attempt,
                    )
                return result

            except BaseException as exc:  # noqa: BLE001
                if _is_auth_error(exc):
                    logger.error(
                        "llm_provider_auth_error",
                        provider=self._primary.name,
                        error=str(exc),
                    )
                    raise  # auth errors are never retried or fallen back

                if not _is_retryable(exc):
                    logger.error(
                        "llm_provider_non_retryable_error",
                        provider=self._primary.name,
                        error=str(exc),
                    )
                    raise  # e.g. safety block, malformed request — propagate as-is

                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "llm_provider_retry",
                        provider=self._primary.name,
                        attempt=attempt,
                        next_attempt=attempt + 1,
                        delay_seconds=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "llm_provider_exhausted",
                        provider=self._primary.name,
                        attempts=self._max_retries,
                        error=str(exc),
                    )

        # --- Fallback provider (single attempt) ---
        if self._fallback is not None:
            logger.info(
                "llm_provider_switching_to_fallback",
                from_provider=self._primary.name,
                to_provider=self._fallback.name,
            )
            try:
                result = await getattr(self._fallback, method)(**kwargs)
                logger.info(
                    "llm_provider_fallback_success",
                    provider=self._fallback.name,
                    method=method,
                )
                return result
            except BaseException as exc:  # noqa: BLE001
                logger.error(
                    "llm_provider_fallback_failed",
                    provider=self._fallback.name,
                    error=str(exc),
                )
                raise ProviderUnavailableError(
                    f"Both {self._primary.name} (after {self._max_retries} retries) "
                    f"and fallback {self._fallback.name} failed. "
                    f"Last primary error: {last_exc}. Fallback error: {exc}"
                ) from exc

        # No fallback configured — surface as unavailable.
        raise ProviderUnavailableError(
            f"Provider '{self._primary.name}' failed after {self._max_retries} retries "
            f"and no fallback is configured. Last error: {last_exc}"
        ) from last_exc
"""LLMPort implementation backed by the Anthropic Claude API (async SDK).

Uses the Messages API with structured outputs (output_config.format) for JSON
responses. Retries transient errors; maps failures to ExternalServiceError.
"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic, APIStatusError, APIConnectionError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.exceptions import ExternalServiceError

logger = get_logger("llm.claude")

_RETRYABLE = (RateLimitError, APIConnectionError)


class ClaudeLLM:
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            logger.warning("anthropic_api_key_missing")
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key or None)
        self._model = settings.claude_model
        self._max_tokens = settings.claude_max_tokens

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete(
        self, *, system: str, user: str, max_tokens: int | None = None
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except _RETRYABLE:
            raise
        except (APIStatusError, Exception) as exc:  # noqa: BLE001
            raise ExternalServiceError(f"Claude request failed: {exc}") from exc

        if response.stop_reason == "refusal":
            raise ExternalServiceError("The model declined to respond to this request.")
        return "".join(b.text for b in response.content if b.type == "text")

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int | None = None,
    ) -> dict:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except _RETRYABLE:
            raise
        except (APIStatusError, Exception) as exc:  # noqa: BLE001
            raise ExternalServiceError(f"Claude request failed: {exc}") from exc

        if response.stop_reason == "refusal":
            raise ExternalServiceError("The model declined to respond to this request.")

        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ExternalServiceError("Model returned malformed JSON.") from exc

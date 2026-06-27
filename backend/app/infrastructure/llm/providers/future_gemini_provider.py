"""Gemini provider via Google AI Studio's OpenAI-compatible endpoint.

Google AI Studio exposes an OpenAI-compatible Chat Completions API at:
  https://generativelanguage.googleapis.com/v1beta/openai

This provider is a thin alias of OpenAICompatProvider — the only difference is
the ``name`` attribute and that the Gemini endpoint uses ``json_schema``
structured-output mode (not ``guided_json`` which is a vLLM-only feature).

Get a free API key at: https://aistudio.google.com
"""
from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.exceptions import ExternalServiceError
from app.infrastructure.llm.base import LLMProvider
from app.infrastructure.llm.openai_compat import OpenAICompatibleClient
from app.infrastructure.llm.structured import (
    parse_json,
    schema_in_prompt,
    schema_instruction,
    structured_body,
)

logger = get_logger("llm.gemini")


class GeminiProvider(LLMProvider):
    """Gemini 2.5 Flash (and family) via Google AI Studio OpenAI-compat API."""

    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self._mode = settings.llm_structured_mode
        self._client = OpenAICompatibleClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            default_max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_request_timeout,
        )

    async def complete(
        self, *, system: str, user: str, max_tokens: int | None = None
    ) -> str:
        return await self._client.chat(system=system, user=user, max_tokens=max_tokens)

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int | None = None,
    ) -> dict:
        prompt = user + (schema_instruction(schema) if schema_in_prompt(self._mode) else "")
        extra = structured_body(schema, self._mode)

        text = await self._client.chat(
            system=system, user=prompt, max_tokens=max_tokens, extra_body=extra
        )
        try:
            return parse_json(text)
        except ValueError:
            logger.warning("llm_json_parse_failed_retrying", mode=self._mode)

        # One repair attempt: force prompt-embedded schema + json_object.
        repair_text = await self._client.chat(
            system=system,
            user=user + schema_instruction(schema),
            max_tokens=max_tokens,
            extra_body={"response_format": {"type": "json_object"}},
        )
        try:
            return parse_json(repair_text)
        except ValueError as exc:
            raise ExternalServiceError("Model returned malformed JSON.") from exc

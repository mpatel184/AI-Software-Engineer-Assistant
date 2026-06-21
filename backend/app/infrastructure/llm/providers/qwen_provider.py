"""Qwen3-Coder provider over an OpenAI-compatible local backend (vLLM/Ollama/LM Studio).

Implements the LLMProvider/LLMPort contract. JSON responses are constrained using
the configured structured-output strategy; for weaker modes the schema is also
embedded in the prompt and the reply is parsed defensively with one repair retry.
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

logger = get_logger("llm.qwen")


class QwenProvider(LLMProvider):
    name = "qwen"

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

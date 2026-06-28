"""GLM provider via Z.ai's OpenAI-compatible endpoint.

Z.ai (open.bigmodel.cn) exposes an OpenAI-compatible Chat Completions API.
This provider is used as the automatic fallback when the primary (Gemini) is
temporarily unavailable.

GLM does not support ``json_schema`` structured-output mode; use
``json_object`` (the universal fallback) and embed the schema in the prompt.

Get an API key at: https://open.bigmodel.cn
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

logger = get_logger("llm.glm")


class GLMProvider(LLMProvider):
    """Z.ai GLM models via the OpenAI-compatible API (fallback provider)."""

    name = "glm"

    def __init__(self, settings: Settings) -> None:
        self._mode = settings.glm_structured_mode
        self._client = OpenAICompatibleClient(
            base_url=settings.glm_base_url,
            api_key=settings.glm_api_key,
            model=settings.glm_model,
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
            logger.warning("glm_json_parse_failed_retrying", mode=self._mode)

        # One repair attempt: strengthen system prompt with schema.
        repair_text = await self._client.chat(
            system=system + schema_instruction(schema),
            user=user,
            max_tokens=max_tokens,
            extra_body={"response_format": {"type": "json_object"}},
        )
        try:
            return parse_json(repair_text)
        except ValueError as exc:
            raise ExternalServiceError("GLM returned malformed JSON.") from exc
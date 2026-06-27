"""Async client for any OpenAI-compatible chat-completions endpoint.

Works unchanged against cloud APIs (Gemini via Google AI Studio, Z.ai GLM,
OpenAI) and self-hosted servers (vLLM, Ollama, LM Studio) — only the base URL
and API key differ.
Transient network/5xx errors are retried with exponential backoff; other failures
are mapped to ExternalServiceError.
"""
from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.domain.exceptions import ExternalServiceError

logger = get_logger("llm.openai_compat")

_RETRYABLE = (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        default_max_tokens: int,
        timeout: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._default_max_tokens = default_max_tokens
        self._timeout = timeout

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def chat(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self._temperature,
            "max_tokens": max_tokens or self._default_max_tokens,
            "stream": False,
        }
        if extra_body:
            payload.update(extra_body)

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
        except _RETRYABLE:
            raise
        except httpx.HTTPError as exc:  # noqa: BLE001
            raise ExternalServiceError(f"LLM request failed: {exc}") from exc

        if response.status_code >= 500:
            # Trigger a retry for transient server errors.
            raise httpx.RemoteProtocolError(f"LLM server error {response.status_code}")
        if response.status_code >= 400:
            raise ExternalServiceError(
                f"LLM request rejected ({response.status_code}): {response.text[:300]}"
            )

        data = response.json()
        try:
            choice = data["choices"][0]
            if choice.get("finish_reason") == "content_filter":
                raise ExternalServiceError("The model declined to respond to this request.")
            return choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ExternalServiceError("Malformed response from LLM server.") from exc

"""Unit tests for the ProviderManager retry/fallback system.

Covers:
- Primary provider success (no fallback needed)
- Primary quota/rate-limit → fallback success
- Primary timeout → fallback success
- Primary auth error → no fallback (immediate raise)
- Fallback unavailable → ProviderUnavailableError
- Retry count before switching
- No fallback configured → ProviderUnavailableError after retries
- Factory configuration loading
- GLM provider missing key → ConfigurationError
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.config import Settings
from app.domain.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    ProviderAuthenticationError,
    ProviderUnavailableError,
)
from app.infrastructure.llm.manager import ProviderManager, _is_auth_error, _is_retryable

# Patch env before Settings is instantiated.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long-xx")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(name: str, side_effect=None, return_value: str = "ok") -> MagicMock:
    """Build a mock LLMProvider."""
    p = MagicMock()
    p.name = name
    if side_effect is not None:
        p.complete = AsyncMock(side_effect=side_effect)
        p.complete_json = AsyncMock(side_effect=side_effect)
    else:
        p.complete = AsyncMock(return_value=return_value)
        p.complete_json = AsyncMock(return_value={"result": return_value})
    return p


def _manager(
    primary,
    fallback=None,
    *,
    max_retries: int = 3,
    backoff: float = 0.0,  # zero delay for unit tests
) -> ProviderManager:
    return ProviderManager(
        primary=primary,
        fallback=fallback,
        max_retries=max_retries,
        retry_backoff=backoff,
    )


# ---------------------------------------------------------------------------
# _is_retryable / _is_auth_error helpers
# ---------------------------------------------------------------------------


def test_retryable_httpx_errors():
    assert _is_retryable(httpx.ConnectError("refused"))
    assert _is_retryable(httpx.ReadTimeout("timed out"))
    assert _is_retryable(httpx.RemoteProtocolError("proto error"))


def test_retryable_external_service_with_rate_limit_message():
    assert _is_retryable(ExternalServiceError("LLM rate limited (429)"))


def test_retryable_external_service_with_server_error_message():
    assert _is_retryable(ExternalServiceError("LLM server error 503"))


def test_non_retryable_external_service():
    assert not _is_retryable(ExternalServiceError("Model declined to respond"))


def test_auth_error_detected_by_status_code_in_message():
    assert _is_auth_error(ExternalServiceError("rejected (401): Unauthorized"))


def test_auth_error_detected_by_class():
    assert _is_auth_error(ProviderAuthenticationError("bad key"))


def test_auth_error_not_flagged_for_503():
    assert not _is_auth_error(ExternalServiceError("LLM server error 503"))


# ---------------------------------------------------------------------------
# ProviderManager — success paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_primary_success_no_fallback_needed():
    primary = _make_provider("gemini", return_value="hello")
    mgr = _manager(primary)

    result = await mgr.complete(system="sys", user="usr")

    assert result == "hello"
    primary.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_primary_success_first_attempt_skips_retries():
    primary = _make_provider("gemini", return_value="hi")
    fallback = _make_provider("glm")
    mgr = _manager(primary, fallback)

    await mgr.complete(system="s", user="u")

    fallback.complete.assert_not_awaited()


# ---------------------------------------------------------------------------
# ProviderManager — retry behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_primary_retries_before_fallback():
    """Primary fails twice with a retryable error, succeeds on third attempt."""
    call_count = 0

    async def flaky(*_, **__):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("refused")
        return "recovered"

    primary = _make_provider("gemini")
    primary.complete = AsyncMock(side_effect=flaky)
    fallback = _make_provider("glm")
    mgr = _manager(primary, fallback, max_retries=3)

    result = await mgr.complete(system="s", user="u")

    assert result == "recovered"
    assert call_count == 3
    fallback.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_count_exact():
    """Primary must be called exactly max_retries times before giving up."""
    primary = _make_provider("gemini", side_effect=httpx.ConnectError("refused"))
    fallback = _make_provider("glm", return_value="fallback-ok")
    mgr = _manager(primary, fallback, max_retries=3)

    await mgr.complete(system="s", user="u")

    assert primary.complete.await_count == 3


# ---------------------------------------------------------------------------
# ProviderManager — fallback paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quota_exceeded_falls_back_to_glm():
    primary = _make_provider(
        "gemini", side_effect=ExternalServiceError("LLM rate limited (429)")
    )
    fallback = _make_provider("glm", return_value="from-glm")
    mgr = _manager(primary, fallback, max_retries=2)

    result = await mgr.complete(system="s", user="u")

    assert result == "from-glm"
    fallback.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_timeout_falls_back_to_glm():
    primary = _make_provider("gemini", side_effect=httpx.ReadTimeout("timeout"))
    fallback = _make_provider("glm", return_value="glm-response")
    mgr = _manager(primary, fallback, max_retries=1)

    result = await mgr.complete(system="s", user="u")

    assert result == "glm-response"


@pytest.mark.asyncio
async def test_complete_json_falls_back_to_glm():
    primary = _make_provider("gemini", side_effect=httpx.ConnectError("refused"))
    fallback = _make_provider("glm")
    fallback.complete_json = AsyncMock(return_value={"answer": 42})
    mgr = _manager(primary, fallback, max_retries=1)

    result = await mgr.complete_json(system="s", user="u", schema={})

    assert result == {"answer": 42}


# ---------------------------------------------------------------------------
# ProviderManager — non-retryable / auth errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_error_does_not_fall_back():
    """An auth error on the primary must NOT cause a fallback attempt."""
    primary = _make_provider(
        "gemini", side_effect=ExternalServiceError("rejected (401): Unauthorized")
    )
    fallback = _make_provider("glm")
    mgr = _manager(primary, fallback)

    with pytest.raises(ExternalServiceError):
        await mgr.complete(system="s", user="u")

    fallback.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_safety_block_does_not_fall_back():
    """Safety/content-filter errors must NOT trigger a fallback."""
    primary = _make_provider(
        "gemini", side_effect=ExternalServiceError("The model declined to respond")
    )
    fallback = _make_provider("glm")
    mgr = _manager(primary, fallback)

    with pytest.raises(ExternalServiceError):
        await mgr.complete(system="s", user="u")

    fallback.complete.assert_not_awaited()


# ---------------------------------------------------------------------------
# ProviderManager — both providers fail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_both_providers_fail_raises_unavailable():
    primary = _make_provider("gemini", side_effect=httpx.ConnectError("refused"))
    fallback = _make_provider("glm", side_effect=ExternalServiceError("glm down"))
    mgr = _manager(primary, fallback, max_retries=1)

    with pytest.raises(ProviderUnavailableError):
        await mgr.complete(system="s", user="u")


@pytest.mark.asyncio
async def test_no_fallback_configured_raises_unavailable():
    primary = _make_provider("gemini", side_effect=httpx.ConnectError("refused"))
    mgr = _manager(primary, fallback=None, max_retries=2)

    with pytest.raises(ProviderUnavailableError):
        await mgr.complete(system="s", user="u")


# ---------------------------------------------------------------------------
# Factory — configuration loading
# ---------------------------------------------------------------------------


_REQUIRED_SETTINGS = {
    "database_url": "postgresql+asyncpg://postgres:postgres@localhost/test",
    "redis_url": "redis://localhost:6379/1",
    "jwt_secret_key": "test-secret-key-at-least-32-characters-long-xx",  # noqa: S106
    "llm_api_key": "fake-gemini-key",
    "debug": False,
    "fallback_provider": "none",
    "glm_api_key": "",
}


def _settings(**overrides: object) -> Settings:
    """Build a Settings instance with test defaults, bypassing env + lru_cache."""
    return Settings(_env_file=None, **{**_REQUIRED_SETTINGS, **overrides})


def test_factory_builds_provider_manager_for_gemini():
    from app.infrastructure.llm.factory import get_llm_provider

    mgr = get_llm_provider(_settings(llm_provider="gemini"))

    assert isinstance(mgr, ProviderManager)
    assert mgr._primary.name == "gemini"
    assert mgr._fallback is None


def test_factory_builds_glm_fallback_when_configured():
    from app.infrastructure.llm.factory import get_llm_provider

    mgr = get_llm_provider(_settings(fallback_provider="glm", glm_api_key="fake-glm-key"))

    assert mgr._fallback is not None
    assert mgr._fallback.name == "glm"


def test_factory_raises_config_error_when_glm_key_missing():
    from app.infrastructure.llm.factory import get_llm_provider

    with pytest.raises(ConfigurationError, match="GLM_API_KEY"):
        get_llm_provider(_settings(fallback_provider="glm", glm_api_key=""))


def test_factory_respects_max_retries_setting():
    from app.infrastructure.llm.factory import get_llm_provider

    mgr = get_llm_provider(_settings(llm_max_retries=5))

    assert mgr._max_retries == 5


def test_factory_respects_retry_backoff_setting():
    from app.infrastructure.llm.factory import get_llm_provider

    mgr = get_llm_provider(_settings(llm_retry_backoff=3.5))

    assert mgr._retry_backoff == pytest.approx(3.5)

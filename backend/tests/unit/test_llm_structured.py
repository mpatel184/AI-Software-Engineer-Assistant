"""Unit tests for the backend-agnostic structured-output strategy and JSON parsing."""
from __future__ import annotations

import pytest

from app.infrastructure.llm.structured import (
    parse_json,
    schema_in_prompt,
    structured_body,
)

_SCHEMA = {"type": "object", "properties": {"x": {"type": "integer"}}}


def test_guided_json_mode_for_vllm():
    assert structured_body(_SCHEMA, "guided_json") == {"guided_json": _SCHEMA}


def test_json_schema_mode_for_lmstudio():
    body = structured_body(_SCHEMA, "json_schema")
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"] == _SCHEMA


def test_ollama_format_mode_passes_schema():
    assert structured_body(_SCHEMA, "ollama_format") == {"format": _SCHEMA}


def test_json_object_fallback():
    assert structured_body(_SCHEMA, "json_object") == {
        "response_format": {"type": "json_object"}
    }


def test_schema_in_prompt_only_for_weak_modes():
    assert schema_in_prompt("json_object") is True
    assert schema_in_prompt("ollama_format") is True
    assert schema_in_prompt("guided_json") is False
    assert schema_in_prompt("json_schema") is False


def test_parse_json_plain():
    assert parse_json('{"x": 1}') == {"x": 1}


def test_parse_json_code_fence():
    assert parse_json('```json\n{"x": 1}\n```') == {"x": 1}


def test_parse_json_with_surrounding_prose():
    assert parse_json('Sure! {"x": 1} done') == {"x": 1}


def test_parse_json_raises_when_no_object():
    with pytest.raises(ValueError):
        parse_json("no json here")

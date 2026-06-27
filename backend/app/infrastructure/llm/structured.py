"""Structured-output strategy for OpenAI-compatible inference backends.

Different local backends constrain JSON output differently:

* vLLM        → ``guided_json`` (grammar-constrained; most reliable)
* LM Studio   → ``response_format: {type: json_schema, ...}``
* Ollama      → ``format: <schema>``
* any server  → ``response_format: {type: json_object}`` + schema in the prompt

This module turns a JSON schema + mode into the extra request body and parses
the model's reply, so the provider stays backend-agnostic.
"""
from __future__ import annotations

import json
import re

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def structured_body(schema: dict, mode: str) -> dict:
    """Return the extra request-body fields that constrain output to `schema`."""
    if mode == "guided_json":
        return {"guided_json": schema}
    if mode == "json_schema":
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": schema, "strict": True},
            }
        }
    if mode == "ollama_format":
        return {"format": schema}
    # json_object / universal fallback
    return {"response_format": {"type": "json_object"}}


def schema_in_prompt(mode: str) -> bool:
    """Whether the schema must also be injected into the prompt (weak modes)."""
    return True  # Always inject for maximum safety with models like Gemini Flash


def schema_instruction(schema: dict) -> str:
    return (
        "\n\nRespond with a single JSON object only — no prose, no markdown — that "
        "conforms exactly to this JSON schema:\n"
        f"{json.dumps(schema)}"
    )


def parse_json(text: str) -> dict:
    """Best-effort parse of a model reply into a JSON object.

    Tolerates code fences and surrounding prose. Raises ValueError if no object
    can be recovered.
    """
    candidate = text.strip()

    # 1. Try parsing directly
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 2. Try parsing from markdown fences
    fenced = _FENCE.search(candidate)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Try parsing from the first { to the last }
    match = _OBJECT.search(candidate)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Model did not return a parseable JSON object.")

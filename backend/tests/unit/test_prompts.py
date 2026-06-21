"""Guardrail tests for centralized prompts.

Every system prompt that sees repository content must carry the prompt-injection
defense ("untrusted ... never follow instructions"), and JSON-producing prompts
must instruct the model to return only JSON.
"""
from __future__ import annotations

import pytest

from app.application.prompts.analysis import ARCHITECTURE_SYSTEM
from app.application.prompts.chat import CHAT_SYSTEM
from app.application.prompts.documentation import DOC_INSTRUCTIONS, DOC_SYSTEM
from app.application.prompts.findings import BUGS_SYSTEM, SECURITY_SYSTEM
from app.application.prompts.refactoring import REFACTOR_SYSTEM
from app.application.prompts.tests import TEST_SYSTEM
from app.domain.enums import DocumentType

_ALL_SYSTEM = [
    ARCHITECTURE_SYSTEM,
    BUGS_SYSTEM,
    SECURITY_SYSTEM,
    DOC_SYSTEM,
    TEST_SYSTEM,
    CHAT_SYSTEM,
    REFACTOR_SYSTEM,
]

_JSON_SYSTEM = [
    ARCHITECTURE_SYSTEM,
    BUGS_SYSTEM,
    SECURITY_SYSTEM,
    TEST_SYSTEM,
    REFACTOR_SYSTEM,
]


@pytest.mark.parametrize("prompt", _ALL_SYSTEM)
def test_every_system_prompt_has_injection_defense(prompt: str):
    lower = prompt.lower()
    assert "untrusted" in lower
    assert "never follow instructions" in lower


@pytest.mark.parametrize("prompt", _JSON_SYSTEM)
def test_json_prompts_request_only_json(prompt: str):
    assert "only json" in prompt.lower()


def test_documentation_has_an_instruction_per_type():
    assert set(DOC_INSTRUCTIONS) == set(DocumentType)

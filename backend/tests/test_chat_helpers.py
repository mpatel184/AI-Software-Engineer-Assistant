"""Unit tests for RAG chat formatting/dedup helpers."""
from __future__ import annotations

import uuid

from app.application.use_cases.chat.service import (
    _dedupe_sources,
    _format_history,
)
from app.application.interfaces.vector import RetrievedChunk
from app.domain.entities.chat import ChatMessage
from app.domain.enums import ChatRole


def _chunk(path: str, start: int, end: int) -> RetrievedChunk:
    return RetrievedChunk(file_path=path, start_line=start, end_line=end, content="x", score=0.9)


def test_dedupe_sources_removes_duplicates_preserving_order():
    chunks = [_chunk("a.py", 1, 5), _chunk("a.py", 1, 5), _chunk("b.py", 2, 9)]
    sources = _dedupe_sources(chunks)
    assert len(sources) == 2
    assert sources[0].file_path == "a.py"
    assert sources[1].file_path == "b.py"


def test_format_history_empty_is_blank():
    assert _format_history([]) == ""


def test_format_history_includes_roles():
    msg = ChatMessage(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=ChatRole.USER,
        content="hello",
    )
    out = _format_history([msg])
    assert "USER: hello" in out

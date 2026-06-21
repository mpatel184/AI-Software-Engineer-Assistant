"""Code symbol entity — a parsed declaration in a repository's source.

Populated by the AST/symbol-extraction layer during indexing and used for code
understanding (hybrid retrieval, documentation grounding, test targeting).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.enums import SymbolKind


@dataclass(slots=True)
class Symbol:
    id: uuid.UUID
    repository_id: uuid.UUID
    file_path: str
    kind: SymbolKind
    name: str
    qualified_name: str
    signature: str
    start_line: int
    end_line: int
    language: str | None = None
    parent_name: str | None = None
    docstring: str | None = None

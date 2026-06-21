"""Backend-neutral result type for symbol extraction.

Extractors return ``ExtractedSymbol`` (no DB identity); the indexing service
assigns repository_id/id when persisting. This keeps parsers free of the
domain/persistence layer and easy to test.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import SymbolKind


@dataclass(slots=True)
class ExtractedSymbol:
    kind: SymbolKind
    name: str
    qualified_name: str
    signature: str
    start_line: int
    end_line: int
    parent_name: str | None = None
    docstring: str | None = None

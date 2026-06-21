"""Build the symbol index for a cloned repository.

Walks source files, extracts symbols via the code-intelligence layer, and maps
them to domain ``Symbol`` entities ready for persistence. Pure orchestration —
no DB or framework dependencies.
"""
from __future__ import annotations

import uuid

from app.application.services.repo_walker import walk_source_files
from app.domain.entities.symbol import Symbol
from app.infrastructure.code_intel.symbol_extractor import extract_symbols

# Cap symbols per repository to keep the index bounded on very large repos.
MAX_SYMBOLS = 50_000


def extract_repository_symbols(clone_path: str, repo_id: uuid.UUID) -> list[Symbol]:
    symbols: list[Symbol] = []
    for source in walk_source_files(clone_path):
        extracted = extract_symbols(
            relative_path=source.relative_path,
            content=source.content,
            language=source.language,
        )
        for s in extracted:
            symbols.append(
                Symbol(
                    id=uuid.uuid4(),
                    repository_id=repo_id,
                    file_path=source.relative_path,
                    kind=s.kind,
                    name=s.name,
                    qualified_name=s.qualified_name,
                    signature=s.signature,
                    start_line=s.start_line,
                    end_line=s.end_line,
                    language=source.language,
                    parent_name=s.parent_name,
                    docstring=s.docstring,
                )
            )
            if len(symbols) >= MAX_SYMBOLS:
                return symbols
    return symbols

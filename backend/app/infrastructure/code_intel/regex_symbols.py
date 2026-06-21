"""Dependency-free heuristic symbol extraction for non-Python languages.

A pragmatic line-based extractor for JS/TS/Java/Go/etc. that captures functions,
classes and common HTTP route registrations. This is intentionally lightweight;
the module is structured so a tree-sitter backend can replace it later without
touching callers.
"""
from __future__ import annotations

import re

from app.infrastructure.code_intel.types import ExtractedSymbol
from app.domain.enums import SymbolKind

# (regex, kind, capture group index for the name)
_PATTERNS: list[tuple[re.Pattern[str], SymbolKind, int]] = [
    (re.compile(r"^\s*(?:export\s+)?(?:public\s+|private\s+|protected\s+)?class\s+(\w+)"), SymbolKind.CLASS, 1),
    (re.compile(r"^\s*(?:export\s+)?interface\s+(\w+)"), SymbolKind.CLASS, 1),
    (re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("), SymbolKind.FUNCTION, 1),
    # const foo = (..) => / const foo = async (..) =>
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"), SymbolKind.FUNCTION, 1),
    # Go: func Name( / func (r Recv) Name(
    (re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)\s*\("), SymbolKind.FUNCTION, 1),
]

# Express/Fastify-style route registration: app.get('/path', ...)
_ROUTE = re.compile(
    r"\b(?:app|router|server)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]"
)


def extract_regex_symbols(content: str) -> list[ExtractedSymbol]:
    symbols: list[ExtractedSymbol] = []
    for i, line in enumerate(content.splitlines(), start=1):
        for pattern, kind, group in _PATTERNS:
            m = pattern.match(line)
            if m:
                name = m.group(group)
                symbols.append(
                    ExtractedSymbol(
                        kind=kind,
                        name=name,
                        qualified_name=name,
                        signature=line.strip()[:200],
                        start_line=i,
                        end_line=i,
                    )
                )
                break
        for rm in _ROUTE.finditer(line):
            label = f"{rm.group(1).upper()} {rm.group(2)}"
            symbols.append(
                ExtractedSymbol(
                    kind=SymbolKind.ROUTE,
                    name=label,
                    qualified_name=label,
                    signature=line.strip()[:200],
                    start_line=i,
                    end_line=i,
                )
            )
    return symbols

"""Dispatch symbol extraction to the best available parser for a file.

Python uses the high-fidelity stdlib `ast`; everything else uses the heuristic
regex extractor. Returns backend-neutral ExtractedSymbol records.
"""
from __future__ import annotations

import os

from app.infrastructure.code_intel.python_ast import extract_python_symbols
from app.infrastructure.code_intel.regex_symbols import extract_regex_symbols
from app.infrastructure.code_intel.types import ExtractedSymbol


def _module_qual(relative_path: str) -> str:
    no_ext = os.path.splitext(relative_path)[0]
    return no_ext.replace("/", ".").replace("\\", ".")


def extract_symbols(
    *, relative_path: str, content: str, language: str | None
) -> list[ExtractedSymbol]:
    if relative_path.endswith(".py"):
        return extract_python_symbols(content, module_qual=_module_qual(relative_path))
    return extract_regex_symbols(content)

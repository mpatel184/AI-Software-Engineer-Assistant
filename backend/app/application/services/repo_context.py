"""Builds a bounded source-code sample from a cloned repository.

Used to feed Claude enough context for documentation/generation without
exceeding token limits. Prioritizes important files and caps total size.
"""
from __future__ import annotations

from app.application.services.repo_walker import SourceFile, walk_source_files

# Files that are most informative for understanding a project, ranked.
_PRIORITY_HINTS = (
    "readme", "main.", "app.", "index.", "__init__", "router", "routes",
    "server.", "settings", "config", "models", "schema", "api",
)

DEFAULT_MAX_CHARS = 48_000


def _priority(path: str) -> int:
    lower = path.lower()
    for i, hint in enumerate(_PRIORITY_HINTS):
        if hint in lower:
            return i
    return len(_PRIORITY_HINTS)


def build_source_sample(
    clone_path: str, *, max_chars: int = DEFAULT_MAX_CHARS, extensions: set[str] | None = None
) -> str:
    """Concatenate a prioritized, size-capped sample of source files."""
    files: list[SourceFile] = list(walk_source_files(clone_path))
    if extensions:
        files = [f for f in files if any(f.relative_path.endswith(e) for e in extensions)]
    files.sort(key=lambda f: (_priority(f.relative_path), f.relative_path))

    parts: list[str] = []
    used = 0
    for f in files:
        header = f"\n\n===== FILE: {f.relative_path} =====\n"
        body = f.content
        remaining = max_chars - used - len(header)
        if remaining <= 0:
            break
        if len(body) > remaining:
            body = body[:remaining] + "\n... (truncated)"
        parts.append(header + body)
        used += len(header) + len(body)

    return "".join(parts)

"""Walk a cloned repository and yield indexable source files.

Deterministic traversal: skips ignored directories, non-source extensions,
oversized and binary files. Used by the indexing pipeline.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from app.application.services.chunking import language_for_extension
from app.core.constants import IGNORED_DIRS, MAX_FILE_SIZE_BYTES, SOURCE_EXTENSIONS


@dataclass(slots=True)
class SourceFile:
    relative_path: str
    content: str
    language: str | None
    line_count: int
    size_bytes: int


def _looks_binary(sample: bytes) -> bool:
    return b"\x00" in sample


def walk_source_files(root: str) -> Iterator[SourceFile]:
    root_path = Path(root).resolve()
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune ignored directories in place so os.walk doesn't descend.
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext not in SOURCE_EXTENSIONS:
                continue

            full = Path(dirpath) / filename
            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size == 0 or size > MAX_FILE_SIZE_BYTES:
                continue

            try:
                raw = full.read_bytes()
            except OSError:
                continue
            if _looks_binary(raw[:1024]):
                continue

            content = raw.decode("utf-8", errors="replace")
            rel = str(full.relative_to(root_path)).replace(os.sep, "/")
            yield SourceFile(
                relative_path=rel,
                content=content,
                language=language_for_extension(ext),
                line_count=content.count("\n") + 1,
                size_bytes=size,
            )

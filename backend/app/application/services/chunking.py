"""Line-based text chunking with overlap for the RAG pipeline.

Pure functions — no I/O — so they are deterministic and unit-testable. Chunking
is line-oriented (not token-oriented) to keep source-code context coherent and
to produce accurate line citations for chat answers.
"""
from __future__ import annotations

import hashlib

from app.application.interfaces.vector import Chunk

# Maps file extensions to a human language label.
EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".cpp": "C++", ".c": "C", ".h": "C", ".hpp": "C++", ".rs": "Rust",
    ".kt": "Kotlin", ".swift": "Swift", ".scala": "Scala", ".sql": "SQL", ".sh": "Shell",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".json": "JSON", ".md": "Markdown",
    ".html": "HTML", ".css": "CSS", ".scss": "CSS",
}

DEFAULT_CHUNK_LINES = 60
DEFAULT_OVERLAP_LINES = 10


def language_for_extension(ext: str) -> str | None:
    return EXTENSION_LANGUAGE.get(ext.lower())


def _estimate_tokens(text: str) -> int:
    # Rough heuristic: ~4 chars per token. Good enough for budgeting.
    return max(1, len(text) // 4)


def chunk_text(
    *,
    file_path: str,
    content: str,
    language: str | None,
    chunk_lines: int = DEFAULT_CHUNK_LINES,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
) -> list[Chunk]:
    """Split file content into overlapping line-windows."""
    if not content.strip():
        return []
    if overlap_lines >= chunk_lines:
        raise ValueError("overlap_lines must be smaller than chunk_lines")

    lines = content.splitlines()
    step = chunk_lines - overlap_lines
    chunks: list[Chunk] = []
    index = 0

    for start in range(0, len(lines), step):
        window = lines[start : start + chunk_lines]
        if not window:
            break
        text = "\n".join(window)
        if not text.strip():
            continue
        chunks.append(
            Chunk(
                file_path=file_path,
                language=language,
                chunk_index=index,
                start_line=start + 1,
                end_line=start + len(window),
                content=text,
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                token_count=_estimate_tokens(text),
            )
        )
        index += 1
        if start + chunk_lines >= len(lines):
            break

    return chunks

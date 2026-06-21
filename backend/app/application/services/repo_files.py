"""Safe access to individual files inside a cloned repository.

All access is constrained to the repository root: a caller-supplied relative
path is resolved and verified to stay within the clone (path-traversal defense)
before any read.
"""
from __future__ import annotations

from pathlib import Path

from app.application.services.repo_walker import walk_source_files
from app.core.constants import MAX_FILE_SIZE_BYTES
from app.domain.exceptions import NotFoundError, ValidationError


def list_source_paths(clone_path: str) -> list[str]:
    """Return sorted relative paths of indexable source files in the repo."""
    return sorted(f.relative_path for f in walk_source_files(clone_path))


def _resolve_within(clone_path: str, relative_path: str) -> Path:
    root = Path(clone_path).resolve()
    candidate = (root / relative_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValidationError("Invalid file path.")
    return candidate


def read_source_file(clone_path: str, relative_path: str) -> str:
    """Read a single source file safely, rejecting traversal and oversized files."""
    if not relative_path or relative_path.strip() != relative_path:
        raise ValidationError("Invalid file path.")

    path = _resolve_within(clone_path, relative_path)
    if not path.is_file():
        raise NotFoundError("File not found in repository.")

    size = path.stat().st_size
    if size == 0:
        raise ValidationError("File is empty.")
    if size > MAX_FILE_SIZE_BYTES:
        raise ValidationError("File is too large to process.")

    raw = path.read_bytes()
    if b"\x00" in raw[:1024]:
        raise ValidationError("Binary files are not supported.")
    return raw.decode("utf-8", errors="replace")

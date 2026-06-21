"""Unit tests for safe single-file repository access (path-traversal defense)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.application.services.repo_files import (
    list_source_paths,
    read_source_file,
)
from app.domain.exceptions import NotFoundError, ValidationError


@pytest.fixture
def repo(tmp_path: Path) -> str:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    # A secret file outside the source tree we must never be able to read via traversal.
    (tmp_path.parent / "secret.txt").write_text("TOPSECRET", encoding="utf-8")
    return str(tmp_path)


def test_list_source_paths_returns_relative_paths(repo: str):
    assert "pkg/main.py" in list_source_paths(repo)


def test_read_source_file_reads_within_repo(repo: str):
    assert "print" in read_source_file(repo, "pkg/main.py")


def test_read_source_file_rejects_parent_traversal(repo: str):
    with pytest.raises(ValidationError):
        read_source_file(repo, "../secret.txt")


def test_read_source_file_rejects_absolute_escape(repo: str):
    with pytest.raises(ValidationError):
        read_source_file(repo, "../../etc/passwd")


def test_read_missing_file_raises_not_found(repo: str):
    with pytest.raises(NotFoundError):
        read_source_file(repo, "pkg/nope.py")

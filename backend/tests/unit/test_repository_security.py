"""Unit tests for repository security helpers and ingestion utilities."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from app.application.services.chunking import chunk_text, language_for_extension
from app.application.services.repo_walker import walk_source_files
from app.core.security import UnsafePathError, ensure_within, validate_github_url
from app.domain.exceptions import ValidationError
from app.infrastructure.storage.archive import extract_zip_safely


# --- GitHub URL validation (SSRF / host allowlist) ---

@pytest.mark.parametrize(
    "url,owner,repo",
    [
        ("https://github.com/psf/requests", "psf", "requests"),
        ("https://github.com/psf/requests.git", "psf", "requests"),
        ("https://github.com/Org-Name/my.repo_name/", "Org-Name", "my.repo_name"),
    ],
)
def test_validate_github_url_accepts_valid(url, owner, repo):
    assert validate_github_url(url) == (owner, repo)


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/psf/requests",          # not https
        "git@github.com:psf/requests.git",          # ssh
        "https://gitlab.com/psf/requests",          # wrong host
        "https://github.com/psf",                   # missing repo
        "https://user:pass@github.com/psf/requests",  # credentials
        "https://github.com.evil.com/psf/requests",   # host spoof
        "file:///etc/passwd",
    ],
)
def test_validate_github_url_rejects_invalid(url):
    with pytest.raises(ValueError):
        validate_github_url(url)


# --- Path traversal guard ---

def test_ensure_within_allows_child(tmp_path: Path):
    target = ensure_within(tmp_path, Path("sub/file.txt"))
    assert str(tmp_path) in str(target)


def test_ensure_within_blocks_escape(tmp_path: Path):
    with pytest.raises(UnsafePathError):
        ensure_within(tmp_path, Path("../../etc/passwd"))


# --- Zip-slip guard ---

def _make_zip(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_extract_zip_safely_extracts_normal(tmp_path: Path):
    zip_bytes = _make_zip({"src/app.py": "print('hi')\n", "README.md": "# hi"})
    zip_file = tmp_path / "u.zip"
    zip_file.write_bytes(zip_bytes)
    dest = tmp_path / "out"
    total = extract_zip_safely(zip_path=str(zip_file), dest_dir=str(dest), max_total_bytes=10_000)
    assert total > 0
    assert (dest / "src" / "app.py").exists()


def test_extract_zip_safely_blocks_zip_slip(tmp_path: Path):
    zip_bytes = _make_zip({"../../evil.txt": "pwned"})
    zip_file = tmp_path / "evil.zip"
    zip_file.write_bytes(zip_bytes)
    with pytest.raises(ValidationError):
        extract_zip_safely(
            zip_path=str(zip_file), dest_dir=str(tmp_path / "out"), max_total_bytes=10_000
        )


def test_extract_zip_safely_blocks_oversize(tmp_path: Path):
    zip_bytes = _make_zip({"big.txt": "x" * 5000})
    zip_file = tmp_path / "big.zip"
    zip_file.write_bytes(zip_bytes)
    with pytest.raises(ValidationError):
        extract_zip_safely(
            zip_path=str(zip_file), dest_dir=str(tmp_path / "out"), max_total_bytes=100
        )


# --- Chunking ---

def test_chunk_text_produces_overlapping_windows():
    content = "\n".join(f"line {i}" for i in range(150))
    chunks = chunk_text(file_path="a.py", content=content, language="Python",
                        chunk_lines=60, overlap_lines=10)
    assert len(chunks) >= 2
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 60
    # Overlap: next chunk starts 50 lines later (chunk_lines - overlap).
    assert chunks[1].start_line == 51
    assert all(c.content_hash for c in chunks)


def test_chunk_text_empty_returns_nothing():
    assert chunk_text(file_path="a.py", content="   \n  ", language=None) == []


def test_language_for_extension():
    assert language_for_extension(".py") == "Python"
    assert language_for_extension(".tsx") == "TypeScript"
    assert language_for_extension(".unknown") is None


# --- Repo walker ---

def test_walk_source_files_filters_ignored_and_binary(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('x')\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("ignored")
    (tmp_path / "image.png").write_bytes(b"\x00\x01\x02")  # non-source ext anyway
    (tmp_path / "data.bin").write_bytes(b"\x00binary")      # not a source ext

    files = list(walk_source_files(str(tmp_path)))
    paths = {f.relative_path for f in files}
    assert "src/main.py" in paths
    assert not any("node_modules" in p for p in paths)
    assert files[0].language == "Python"

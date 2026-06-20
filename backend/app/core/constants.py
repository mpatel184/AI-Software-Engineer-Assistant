"""Shared, non-secret constants."""
from __future__ import annotations

# Files/dirs skipped during repository indexing.
IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
        ".next", ".mypy_cache", ".pytest_cache", ".ruff_cache", "target", "vendor",
        ".idea", ".vscode", "coverage", "htmlcov",
    }
)

# Extensions indexed for RAG / analysis (source code + docs).
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php", ".cs",
        ".cpp", ".c", ".h", ".hpp", ".rs", ".kt", ".swift", ".scala", ".sql",
        ".sh", ".yaml", ".yml", ".toml", ".json", ".md", ".html", ".css", ".scss",
    }
)

# Hard cap on a single file's size to index (bytes).
MAX_FILE_SIZE_BYTES: int = 1_000_000

# Default RAG retrieval depth.
DEFAULT_RETRIEVAL_K: int = 6

# Pagination defaults.
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

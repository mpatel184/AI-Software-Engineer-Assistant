"""Security helpers: GitHub URL validation and path-traversal guards.

These defend against SSRF (cloning arbitrary hosts), path traversal, and
zip-slip during repository ingestion.
"""
from __future__ import annotations

import re
from pathlib import Path

# Owner/repo per GitHub naming rules; optional .git suffix; https only.
_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})?)/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100}?)"
    r"(?:\.git)?/?$"
)


class UnsafePathError(Exception):
    """Raised when a path escapes its intended root."""


def validate_github_url(url: str) -> tuple[str, str]:
    """Validate a public GitHub HTTPS URL. Returns (owner, repo).

    Rejects SSH, non-github hosts, credentials in URL, and anything else that
    could lead to SSRF or cloning untrusted hosts.
    """
    candidate = url.strip()
    match = _GITHUB_URL_RE.match(candidate)
    if not match:
        raise ValueError(
            "Only public GitHub HTTPS URLs are supported "
            "(https://github.com/<owner>/<repo>)."
        )
    return match.group("owner"), match.group("repo")


def ensure_within(root: Path, target: Path) -> Path:
    """Return the resolved target iff it stays within root; else raise.

    Use for every filesystem write derived from untrusted input (zip entries,
    file paths from a cloned repo).
    """
    root_resolved = root.resolve()
    target_resolved = (root / target).resolve() if not target.is_absolute() else target.resolve()
    if root_resolved != target_resolved and root_resolved not in target_resolved.parents:
        raise UnsafePathError(f"Path escapes its root: {target}")
    return target_resolved

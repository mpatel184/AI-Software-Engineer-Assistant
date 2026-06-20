"""Port for cloning and inspecting git repositories."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class CloneResult:
    clone_path: str
    default_branch: str
    commit_sha: str
    file_count: int
    total_lines: int
    size_bytes: int
    primary_language: str | None
    languages: dict[str, float] = field(default_factory=dict)


class GitPort(Protocol):
    async def clone(self, *, github_url: str, dest_dir: str) -> CloneResult:
        """Shallow-clone the repo into dest_dir and return computed stats."""

    async def remove(self, clone_path: str) -> None:
        """Delete a cloned working tree from disk."""

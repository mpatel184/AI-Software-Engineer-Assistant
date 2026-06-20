"""GitPort implementation using GitPython.

Performs a shallow clone into a sandboxed per-repo directory, then computes
language/line/size statistics by walking the working tree.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from git import GitCommandError, Repo

from app.application.interfaces.git import CloneResult, GitPort
from app.application.services.repo_walker import walk_source_files
from app.core.security import validate_github_url
from app.domain.exceptions import ExternalServiceError, ValidationError


class GitClient(GitPort):
    def __init__(self, *, max_size_bytes: int) -> None:
        self._max_size_bytes = max_size_bytes

    async def clone(self, *, github_url: str, dest_dir: str) -> CloneResult:
        # Re-validate at the boundary even though the use case already did.
        validate_github_url(github_url)
        return await asyncio.to_thread(self._clone_sync, github_url, dest_dir)

    def _clone_sync(self, github_url: str, dest_dir: str) -> CloneResult:
        dest = Path(dest_dir)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)

        try:
            repo = Repo.clone_from(
                github_url,
                dest,
                multi_options=["--depth=1", "--single-branch"],
            )
        except GitCommandError as exc:
            shutil.rmtree(dest, ignore_errors=True)
            raise ExternalServiceError(f"Failed to clone repository: {exc.stderr or exc}") from exc

        commit_sha = repo.head.commit.hexsha
        try:
            default_branch = repo.active_branch.name
        except TypeError:
            default_branch = "HEAD"

        stats = self._compute_stats(dest)
        if stats["size_bytes"] > self._max_size_bytes:
            shutil.rmtree(dest, ignore_errors=True)
            raise ValidationError("Repository exceeds the maximum allowed size.")

        return CloneResult(
            clone_path=str(dest),
            default_branch=default_branch,
            commit_sha=commit_sha,
            file_count=stats["file_count"],
            total_lines=stats["total_lines"],
            size_bytes=stats["size_bytes"],
            primary_language=stats["primary_language"],
            languages=stats["languages"],
        )

    @staticmethod
    def _compute_stats(root: Path) -> dict:
        lines_by_lang: dict[str, int] = {}
        file_count = 0
        total_lines = 0
        size_bytes = 0

        for source in walk_source_files(str(root)):
            file_count += 1
            total_lines += source.line_count
            size_bytes += source.size_bytes
            if source.language:
                lines_by_lang[source.language] = (
                    lines_by_lang.get(source.language, 0) + source.line_count
                )

        total_lang_lines = sum(lines_by_lang.values()) or 1
        languages = {
            lang: round(count * 100 / total_lang_lines, 1)
            for lang, count in sorted(lines_by_lang.items(), key=lambda x: x[1], reverse=True)
        }
        primary = next(iter(languages), None)
        return {
            "file_count": file_count,
            "total_lines": total_lines,
            "size_bytes": size_bytes,
            "languages": languages,
            "primary_language": primary,
        }

    async def remove(self, clone_path: str) -> None:
        await asyncio.to_thread(shutil.rmtree, clone_path, True)

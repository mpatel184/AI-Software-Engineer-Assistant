"""Unit-test generation use case (synchronous, per file).

Given a file in an indexed repository, ask Claude to produce a unit-test suite
for it. The file contents are wrapped as untrusted data. Generation is fast
enough (single file) to run inline on the request rather than via a worker.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.application.interfaces.llm import LLMPort, wrap_untrusted
from app.application.interfaces.repositories import RepositoryRepository
from app.application.prompts.tests import TEST_SYSTEM
from app.application.services.repo_files import list_source_paths, read_source_file
from app.domain.enums import RepoStatus
from app.domain.exceptions import NotFoundError, ValidationError

_SYSTEM = TEST_SYSTEM

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "framework": {"type": "string"},
        "test_file_path": {"type": "string"},
        "test_code": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["framework", "test_file_path", "test_code", "notes"],
}


@dataclass(slots=True)
class GeneratedTest:
    file_path: str
    framework: str
    test_file_path: str
    test_code: str
    notes: str


class TestGenerationService:
    def __init__(
        self, *, repositories: RepositoryRepository, llm: LLMPort
    ) -> None:
        self._repos = repositories
        self._llm = llm

    async def _ready_repo(self, user_id: uuid.UUID, repo_id: uuid.UUID):
        repo = await self._repos.get_for_user(repo_id, user_id)
        if repo is None:
            raise NotFoundError("Repository not found.")
        if repo.status is not RepoStatus.READY:
            raise ValidationError("Repository must be fully indexed first.")
        if not repo.clone_path:
            raise ValidationError("Repository working tree is unavailable.")
        return repo

    async def list_files(self, *, user_id: uuid.UUID, repo_id: uuid.UUID) -> list[str]:
        repo = await self._ready_repo(user_id, repo_id)
        return list_source_paths(repo.clone_path)

    async def generate(
        self, *, user_id: uuid.UUID, repo_id: uuid.UUID, file_path: str
    ) -> GeneratedTest:
        repo = await self._ready_repo(user_id, repo_id)
        source = read_source_file(repo.clone_path, file_path)

        result = await self._llm.complete_json(
            system=_SYSTEM,
            user=(
                f"Generate a unit-test suite for the file `{file_path}`.\n\n"
                + wrap_untrusted(source, label="source file")
            ),
            schema=_SCHEMA,
            max_tokens=8000,
        )
        return GeneratedTest(
            file_path=file_path,
            framework=result.get("framework", ""),
            test_file_path=result.get("test_file_path", ""),
            test_code=result.get("test_code", ""),
            notes=result.get("notes", ""),
        )

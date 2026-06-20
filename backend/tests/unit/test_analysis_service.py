"""Unit tests for AnalysisService and the RunAnalysisService pipeline (fakes)."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.application.use_cases.analysis.run import RunAnalysisService, _health_score
from app.application.use_cases.analysis.service import AnalysisService
from app.domain.entities.analysis import Analysis
from app.domain.entities.repository import Repository
from app.domain.enums import AnalysisType, JobStatus, RepoSource, RepoStatus
from app.domain.exceptions import NotFoundError, ValidationError


class FakeRepoRepo:
    def __init__(self, repo: Repository | None = None):
        self.repo = repo

    async def get_for_user(self, repo_id, user_id):
        if self.repo and self.repo.id == repo_id and self.repo.user_id == user_id:
            return self.repo
        return None

    async def get(self, repo_id):
        return self.repo if self.repo and self.repo.id == repo_id else None


class FakeAnalysisRepo:
    def __init__(self):
        self.items: dict[uuid.UUID, Analysis] = {}

    async def create(self, analysis):
        self.items[analysis.id] = analysis
        return analysis

    async def get(self, analysis_id):
        return self.items.get(analysis_id)

    async def update(self, analysis):
        self.items[analysis.id] = analysis
        return analysis

    async def list_for_repository(self, repo_id, *, type=None):
        return [a for a in self.items.values() if a.repository_id == repo_id]

    async def latest(self, repo_id, type):
        items = [a for a in self.items.values() if a.repository_id == repo_id and a.type == type]
        return items[-1] if items else None

    async def update_status(self, analysis_id, status, *, error_message=None):
        if analysis_id in self.items:
            self.items[analysis_id].status = status
            self.items[analysis_id].error_message = error_message


class FakeDispatcher:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, analysis_id):
        self.enqueued.append(analysis_id)


def _repo(user_id, status=RepoStatus.READY, clone_path="/data/repos/x"):
    return Repository(
        id=uuid.uuid4(),
        user_id=user_id,
        name="demo",
        source=RepoSource.GITHUB,
        status=status,
        clone_path=clone_path,
    )


async def test_trigger_requires_ready_repo():
    user = uuid.uuid4()
    repo = _repo(user, status=RepoStatus.INDEXING)
    svc = AnalysisService(
        repositories=FakeRepoRepo(repo), analyses=FakeAnalysisRepo(), dispatcher=FakeDispatcher()
    )
    with pytest.raises(ValidationError):
        await svc.trigger(user_id=user, repo_id=repo.id, type=AnalysisType.ARCHITECTURE)


async def test_trigger_creates_and_dispatches():
    user = uuid.uuid4()
    repo = _repo(user)
    dispatcher = FakeDispatcher()
    svc = AnalysisService(
        repositories=FakeRepoRepo(repo), analyses=FakeAnalysisRepo(), dispatcher=dispatcher
    )
    analysis = await svc.trigger(user_id=user, repo_id=repo.id, type=AnalysisType.ARCHITECTURE)
    assert analysis.status is JobStatus.QUEUED
    assert dispatcher.enqueued == [analysis.id]


async def test_get_is_owner_scoped():
    owner = uuid.uuid4()
    repo = _repo(owner)
    analyses = FakeAnalysisRepo()
    svc = AnalysisService(repositories=FakeRepoRepo(repo), analyses=analyses, dispatcher=FakeDispatcher())
    a = await svc.trigger(user_id=owner, repo_id=repo.id, type=AnalysisType.ARCHITECTURE)
    # Another user cannot read it (repo ownership check fails)
    with pytest.raises(NotFoundError):
        await svc.get(user_id=uuid.uuid4(), analysis_id=a.id)


class FakeLLM:
    async def complete(self, *, system, user, max_tokens=None):
        return "ok"

    async def complete_json(self, *, system, user, schema, max_tokens=None):
        # Ensure untrusted wrapping is present in the prompt.
        assert "untrusted" in user.lower()
        return {
            "project_summary": "A demo project.",
            "architecture_overview": "Layered.",
            "tech_stack": ["Python"],
            "folder_explanation": [{"path": "src", "purpose": "source"}],
        }


async def test_run_pipeline_completes(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f():\n    if 1:\n        return 2\n")
    user = uuid.uuid4()
    repo = _repo(user, clone_path=str(tmp_path))
    analyses = FakeAnalysisRepo()
    analysis = Analysis(
        id=uuid.uuid4(),
        repository_id=repo.id,
        type=AnalysisType.ARCHITECTURE,
        status=JobStatus.QUEUED,
    )
    await analyses.create(analysis)

    runner = RunAnalysisService(analyses=analyses, repositories=FakeRepoRepo(repo), llm=FakeLLM())
    await runner.run(analysis.id)

    done = analyses.items[analysis.id]
    assert done.status is JobStatus.COMPLETED
    assert done.summary["project_summary"] == "A demo project."
    assert done.metrics["file_count"] == 1
    assert 0 <= done.score <= 100


def test_health_score_bounds():
    assert _health_score({"doc_coverage_pct": 0, "avg_complexity": 100}) >= 0
    assert _health_score({"doc_coverage_pct": 100, "avg_complexity": 0}) <= 100

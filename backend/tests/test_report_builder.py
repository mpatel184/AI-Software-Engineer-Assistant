"""Unit tests for the deterministic report builder."""
from __future__ import annotations

import uuid

from app.application.services.report_builder import build_report
from app.domain.entities.analysis import Analysis
from app.domain.entities.repository import Repository
from app.domain.enums import (
    AnalysisType,
    JobStatus,
    ReportType,
    RepoSource,
    RepoStatus,
)


def _repo() -> Repository:
    return Repository(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="demo",
        source=RepoSource.UPLOAD,
        status=RepoStatus.READY,
    )


def _architecture() -> Analysis:
    return Analysis(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        type=AnalysisType.ARCHITECTURE,
        status=JobStatus.COMPLETED,
        summary={"project_summary": "A demo project.", "tech_stack": ["Python"]},
        metrics={"file_count": 10, "total_lines": 1000},
        score=88,
    )


def _security() -> Analysis:
    return Analysis(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        type=AnalysisType.SECURITY,
        status=JobStatus.COMPLETED,
        summary={
            "overview": "One issue found.",
            "findings": [
                {
                    "title": "Hardcoded secret",
                    "category": "hardcoded_secret",
                    "severity": "high",
                    "file_path": "app.py",
                    "line": 3,
                    "description": "A secret is hardcoded.",
                    "recommendation": "Use env vars.",
                }
            ],
        },
        metrics={"counts": {"high": 1}, "total_findings": 1},
    )


def test_full_report_includes_all_sections():
    title, content = build_report(
        repo=_repo(),
        report_type=ReportType.FULL,
        architecture=_architecture(),
        bugs=None,
        security=_security(),
    )
    assert "Full Repository Report — demo" in title
    assert "## Architecture Overview" in content
    assert "## Bug Detection" in content  # placeholder section present
    assert "## Security" in content
    assert "Hardcoded secret" in content


def test_analysis_report_excludes_findings_sections():
    _, content = build_report(
        repo=_repo(),
        report_type=ReportType.ANALYSIS,
        architecture=_architecture(),
        bugs=None,
        security=_security(),
    )
    assert "## Architecture Overview" in content
    assert "## Security" not in content


def test_missing_analysis_renders_placeholder():
    _, content = build_report(
        repo=_repo(),
        report_type=ReportType.ANALYSIS,
        architecture=None,
        bugs=None,
        security=None,
    )
    assert "No architecture analysis available yet." in content

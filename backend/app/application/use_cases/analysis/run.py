"""Analysis execution pipeline (runs in the worker).

Computes deterministic metrics, builds a compact repository digest, asks Claude
for a narrative architecture overview (repo content wrapped as untrusted data),
then persists summary + metrics + a health score.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from app.application.interfaces.llm import LLMPort, wrap_untrusted
from app.application.prompts.analysis import ARCHITECTURE_SYSTEM
from app.application.interfaces.repositories import (
    AnalysisRepository,
    RepositoryRepository,
)
from app.application.services.code_metrics import compute_metrics
from app.application.use_cases.analysis.findings import run_findings_scan
from app.core.logging import get_logger
from app.domain.enums import AnalysisType, JobStatus
from app.domain.exceptions import NotFoundError

_FINDING_TYPES = {AnalysisType.BUGS, AnalysisType.SECURITY}

logger = get_logger("analysis.run")

_SYSTEM = ARCHITECTURE_SYSTEM

_SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "project_summary": {"type": "string"},
        "architecture_overview": {"type": "string"},
        "tech_stack": {"type": "array", "items": {"type": "string"}},
        "folder_explanation": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {"type": "string"},
                    "purpose": {"type": "string"},
                },
                "required": ["path", "purpose"],
            },
        },
    },
    "required": [
        "project_summary",
        "architecture_overview",
        "tech_stack",
        "folder_explanation",
    ],
}


def _health_score(metrics: dict) -> int:
    """Simple 0-100 health score from doc coverage and complexity."""
    doc = float(metrics.get("doc_coverage_pct", 0))
    avg_cx = float(metrics.get("avg_complexity", 0))
    doc_score = min(doc, 40)  # up to 40 pts for documentation
    cx_score = max(0, 40 - avg_cx)  # lower complexity scores higher (cap 40)
    base = 20  # baseline for a successfully analyzed repo
    return int(min(100, base + doc_score + cx_score))


def _build_digest(repo_name: str, metrics: dict) -> str:
    compact = {
        "name": repo_name,
        "languages": metrics.get("languages", {}),
        "file_count": metrics.get("file_count", 0),
        "total_lines": metrics.get("total_lines", 0),
        "dependencies": metrics.get("dependencies", {}),
        "folder_summary": metrics.get("folder_summary", []),
        "complexity": {
            "avg": metrics.get("avg_complexity", 0),
            "max": metrics.get("max_complexity", 0),
            "hotspots": metrics.get("complexity_hotspots", [])[:5],
        },
        "doc_coverage_pct": metrics.get("doc_coverage_pct", 0),
    }
    return json.dumps(compact, indent=2)


class RunAnalysisService:
    def __init__(
        self,
        *,
        analyses: AnalysisRepository,
        repositories: RepositoryRepository,
        llm: LLMPort,
    ) -> None:
        self._analyses = analyses
        self._repos = repositories
        self._llm = llm

    async def run(self, analysis_id: uuid.UUID) -> None:
        analysis = await self._analyses.get(analysis_id)
        if analysis is None:
            raise NotFoundError("Analysis not found.")
        repo = await self._repos.get(analysis.repository_id)
        if repo is None or not repo.clone_path:
            await self._analyses.update_status(
                analysis_id, JobStatus.FAILED, error_message="Repository unavailable."
            )
            raise NotFoundError("Repository working tree unavailable.")

        try:
            analysis.status = JobStatus.RUNNING
            analysis.started_at = datetime.now(UTC)
            await self._analyses.update(analysis)

            if analysis.type in _FINDING_TYPES:
                summary, metrics, score = await run_findings_scan(
                    scan_type=analysis.type,
                    repo_name=repo.name,
                    clone_path=repo.clone_path,
                    llm=self._llm,
                )
            else:
                metrics = compute_metrics(repo.clone_path).to_dict()
                digest = _build_digest(repo.name, metrics)
                summary = await self._llm.complete_json(
                    system=_SYSTEM,
                    user=(
                        "Analyze this repository digest and produce the assessment.\n\n"
                        + wrap_untrusted(digest, label="repository digest")
                    ),
                    schema=_SUMMARY_SCHEMA,
                )
                score = _health_score(metrics)

            analysis.metrics = metrics
            analysis.summary = summary
            analysis.score = score
            analysis.status = JobStatus.COMPLETED
            analysis.completed_at = datetime.now(UTC)
            await self._analyses.update(analysis)
            logger.info(
                "analysis_complete",
                analysis_id=str(analysis_id),
                type=analysis.type.value,
                score=analysis.score,
            )

        except Exception as exc:  # noqa: BLE001
            logger.exception("analysis_failed", analysis_id=str(analysis_id))
            await self._analyses.update_status(
                analysis_id, JobStatus.FAILED, error_message=str(exc)[:500]
            )
            raise

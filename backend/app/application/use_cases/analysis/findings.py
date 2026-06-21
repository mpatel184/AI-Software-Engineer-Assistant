"""Finding-based scan pipeline (bug detection & security scanning).

Bugs and security scans share the same shape — a list of severity-rated
findings — so they share one pipeline parameterized by scan type. Results are
stored in the Analysis ``summary`` ({"overview", "findings"}) and ``metrics``
({"counts", "total_findings"}), keeping to the existing ``analyses`` schema.

Repository source is wrapped as untrusted data before being sent to Claude.
"""
from __future__ import annotations

from app.application.interfaces.llm import LLMPort, wrap_untrusted
from app.application.prompts.findings import (
    BUGS_INSTRUCTION,
    BUGS_SYSTEM,
    SECURITY_INSTRUCTION,
    SECURITY_SYSTEM,
)
from app.application.services.repo_context import build_source_sample
from app.domain.enums import AnalysisType, Severity

# Severity weights for the 0-100 risk-free "health" score (higher = healthier).
_SEVERITY_PENALTY: dict[str, int] = {
    Severity.CRITICAL.value: 25,
    Severity.HIGH.value: 15,
    Severity.MEDIUM.value: 8,
    Severity.LOW.value: 3,
    Severity.INFO.value: 1,
}

_MODE = {
    AnalysisType.BUGS: (BUGS_SYSTEM, BUGS_INSTRUCTION),
    AnalysisType.SECURITY: (SECURITY_SYSTEM, SECURITY_INSTRUCTION),
}

_FINDINGS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overview": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "category": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": [s.value for s in Severity],
                    },
                    "file_path": {"type": "string"},
                    "line": {"type": "integer"},
                    "description": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
                "required": [
                    "title",
                    "category",
                    "severity",
                    "file_path",
                    "line",
                    "description",
                    "recommendation",
                ],
            },
        },
    },
    "required": ["overview", "findings"],
}


def _counts(findings: list[dict]) -> dict[str, int]:
    counts = {s.value: 0 for s in Severity}
    for f in findings:
        sev = str(f.get("severity", "")).lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def _score(counts: dict[str, int]) -> int:
    penalty = sum(_SEVERITY_PENALTY.get(sev, 0) * n for sev, n in counts.items())
    return max(0, 100 - penalty)


async def run_findings_scan(
    *,
    scan_type: AnalysisType,
    repo_name: str,
    clone_path: str,
    llm: LLMPort,
) -> tuple[dict, dict, int]:
    """Run a finding-based scan. Returns (summary, metrics, score)."""
    system, instruction = _MODE[scan_type]

    sample = build_source_sample(clone_path)
    if not sample.strip():
        raise ValueError("No source files available to scan.")

    result = await llm.complete_json(
        system=system,
        user=(
            f"Repository: {repo_name}\n\n{instruction}\n\n"
            "Return an overview sentence and the list of findings. If there are no "
            "issues, return an empty findings array.\n\n"
            + wrap_untrusted(sample, label="repository source")
        ),
        schema=_FINDINGS_SCHEMA,
        max_tokens=8000,
    )

    findings = result.get("findings", [])
    counts = _counts(findings)
    summary = {"overview": result.get("overview", ""), "findings": findings}
    metrics = {"counts": counts, "total_findings": len(findings)}
    return summary, metrics, _score(counts)

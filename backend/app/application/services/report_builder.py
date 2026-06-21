"""Assemble a Markdown report from a repository's existing analyses.

Pure, deterministic formatting — no external calls. The report is composed from
the architecture analysis plus the bug and security finding scans, filtered by
the requested report type.
"""
from __future__ import annotations

from app.domain.entities.analysis import Analysis
from app.domain.entities.repository import Repository
from app.domain.enums import ReportType

_TITLES = {
    ReportType.FULL: "Full Repository Report",
    ReportType.ANALYSIS: "Architecture Report",
    ReportType.BUGS: "Bug Detection Report",
    ReportType.SECURITY: "Security Report",
}

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def _architecture_section(analysis: Analysis) -> str:
    s = analysis.summary or {}
    m = analysis.metrics or {}
    lines = ["## Architecture Overview", ""]
    if s.get("project_summary"):
        lines += [s["project_summary"], ""]
    if s.get("architecture_overview"):
        lines += ["### Design", s["architecture_overview"], ""]
    if s.get("tech_stack"):
        lines += ["### Technology Stack", ", ".join(s["tech_stack"]), ""]

    lines += [
        "### Metrics",
        f"- Files: {m.get('file_count', '—')}",
        f"- Lines of code: {m.get('total_lines', '—')}",
        f"- Documentation coverage: {m.get('doc_coverage_pct', 0)}%",
        f"- Average complexity: {m.get('avg_complexity', '—')}",
        f"- Health score: {analysis.score if analysis.score is not None else '—'}/100",
        "",
    ]
    folders = s.get("folder_explanation") or []
    if folders:
        lines.append("### Project Structure")
        for f in folders:
            lines.append(f"- `{f.get('path', '')}` — {f.get('purpose', '')}")
        lines.append("")
    return "\n".join(lines)


def _findings_section(title: str, analysis: Analysis) -> str:
    s = analysis.summary or {}
    m = analysis.metrics or {}
    counts = m.get("counts", {})
    findings = s.get("findings", [])

    lines = [f"## {title}", ""]
    if s.get("overview"):
        lines += [s["overview"], ""]
    lines.append(
        "**Findings by severity:** "
        + ", ".join(f"{sev} {counts.get(sev, 0)}" for sev in _SEVERITY_ORDER)
    )
    lines.append("")

    if not findings:
        lines += ["No issues were found.", ""]
        return "\n".join(lines)

    ordered = sorted(
        findings,
        key=lambda f: _SEVERITY_ORDER.index(f.get("severity", "info"))
        if f.get("severity") in _SEVERITY_ORDER
        else len(_SEVERITY_ORDER),
    )
    for f in ordered:
        loc = f.get("file_path", "")
        if f.get("line"):
            loc += f":{f['line']}"
        lines += [
            f"### [{str(f.get('severity', '')).upper()}] {f.get('title', '')}",
            f"*{f.get('category', '')}* · `{loc}`",
            "",
            f.get("description", ""),
            "",
            f"**Recommendation:** {f.get('recommendation', '')}",
            "",
        ]
    return "\n".join(lines)


def build_report(
    *,
    repo: Repository,
    report_type: ReportType,
    architecture: Analysis | None,
    bugs: Analysis | None,
    security: Analysis | None,
) -> tuple[str, str]:
    """Return (title, markdown_content) for the requested report type."""
    title = f"{_TITLES[report_type]} — {repo.name}"
    parts = [f"# {title}", ""]

    want_arch = report_type in (ReportType.FULL, ReportType.ANALYSIS)
    want_bugs = report_type in (ReportType.FULL, ReportType.BUGS)
    want_sec = report_type in (ReportType.FULL, ReportType.SECURITY)

    if want_arch:
        parts.append(
            _architecture_section(architecture)
            if architecture
            else "## Architecture Overview\n\nNo architecture analysis available yet.\n"
        )
    if want_bugs:
        parts.append(
            _findings_section("Bug Detection", bugs)
            if bugs
            else "## Bug Detection\n\nNo bug scan available yet.\n"
        )
    if want_sec:
        parts.append(
            _findings_section("Security", security)
            if security
            else "## Security\n\nNo security scan available yet.\n"
        )

    return title, "\n".join(parts)

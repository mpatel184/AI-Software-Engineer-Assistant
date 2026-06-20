"""Deterministic repository metrics computed without the LLM.

Produces complexity estimates, dependency manifests, a folder summary, and a
documentation-coverage heuristic. Kept free of external services so it is fast,
reproducible, and unit-testable.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.application.services.repo_walker import SourceFile, walk_source_files

# Keywords that introduce a branch/decision point (rough cyclomatic proxy).
_BRANCH_RE = re.compile(
    r"\b(if|elif|else if|for|while|case|catch|except|&&|\|\||\?)\b|\?\."
)
_FUNC_RE = re.compile(r"\b(def|function|func|fn)\b|=>")
_COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*|<!--)")


@dataclass(slots=True)
class FileComplexity:
    file_path: str
    lines: int
    estimated_complexity: int


@dataclass(slots=True)
class CodeMetrics:
    file_count: int = 0
    total_lines: int = 0
    languages: dict[str, float] = field(default_factory=dict)
    avg_complexity: float = 0.0
    max_complexity: int = 0
    complexity_hotspots: list[dict] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    doc_coverage_pct: float = 0.0
    folder_summary: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _file_complexity(content: str) -> int:
    branches = len(_BRANCH_RE.findall(content))
    functions = len(_FUNC_RE.findall(content))
    # Base 1 + decision points; functions add minor structural weight.
    return 1 + branches + functions // 2


def _doc_coverage(files: list[SourceFile]) -> float:
    total = 0
    commented = 0
    for f in files:
        for line in f.content.splitlines():
            if not line.strip():
                continue
            total += 1
            if _COMMENT_RE.match(line):
                commented += 1
    return round(commented * 100 / total, 1) if total else 0.0


def _parse_dependencies(root: Path) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}

    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            node = sorted({*data.get("dependencies", {}), *data.get("devDependencies", {})})
            if node:
                deps["node"] = node
        except (json.JSONDecodeError, OSError):
            pass

    for req_name in ("requirements.txt", "requirements-dev.txt"):
        req = root / req_name
        if req.is_file():
            try:
                lines = req.read_text(encoding="utf-8", errors="replace").splitlines()
                pkgs = [
                    re.split(r"[<>=!~ \[]", ln.strip())[0]
                    for ln in lines
                    if ln.strip() and not ln.strip().startswith("#")
                ]
                deps.setdefault("python", []).extend(p for p in pkgs if p)
            except OSError:
                pass

    pyproject = root / "pyproject.toml"
    if pyproject.is_file() and "python" not in deps:
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
            block = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
            if block:
                found = re.findall(r'["\']([A-Za-z0-9_.-]+)', block.group(1))
                if found:
                    deps["python"] = sorted(set(found))
        except OSError:
            pass

    if (root / "go.mod").is_file():
        deps.setdefault("go", [])
    if (root / "pom.xml").is_file() or (root / "build.gradle").is_file():
        deps.setdefault("java", [])

    return deps


def _folder_summary(files: list[SourceFile]) -> list[dict]:
    by_dir: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0})
    for f in files:
        top = f.relative_path.split("/", 1)[0] if "/" in f.relative_path else "(root)"
        by_dir[top]["files"] += 1
        by_dir[top]["lines"] += f.line_count
    summary = [{"path": k, **v} for k, v in by_dir.items()]
    summary.sort(key=lambda x: x["lines"], reverse=True)
    return summary[:25]


def compute_metrics(clone_path: str) -> CodeMetrics:
    files = list(walk_source_files(clone_path))
    if not files:
        return CodeMetrics()

    complexities: list[FileComplexity] = []
    lines_by_lang: dict[str, int] = defaultdict(int)
    total_lines = 0

    for f in files:
        total_lines += f.line_count
        if f.language:
            lines_by_lang[f.language] += f.line_count
        complexities.append(
            FileComplexity(f.relative_path, f.line_count, _file_complexity(f.content))
        )

    total_lang = sum(lines_by_lang.values()) or 1
    languages = {
        lang: round(n * 100 / total_lang, 1)
        for lang, n in sorted(lines_by_lang.items(), key=lambda x: x[1], reverse=True)
    }

    scores = [c.estimated_complexity for c in complexities]
    avg = round(sum(scores) / len(scores), 1)
    hotspots = sorted(complexities, key=lambda c: c.estimated_complexity, reverse=True)[:10]

    return CodeMetrics(
        file_count=len(files),
        total_lines=total_lines,
        languages=languages,
        avg_complexity=avg,
        max_complexity=max(scores),
        complexity_hotspots=[asdict(h) for h in hotspots],
        dependencies=_parse_dependencies(Path(clone_path)),
        doc_coverage_pct=_doc_coverage(files),
        folder_summary=_folder_summary(files),
    )

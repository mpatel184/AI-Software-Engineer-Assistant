"""Unit tests for the deterministic code-metrics service."""
from __future__ import annotations

import json
from pathlib import Path

from app.application.services.code_metrics import compute_metrics


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_compute_metrics_basic(tmp_path: Path):
    _write(tmp_path, "src/app.py", "def f(x):\n    if x:\n        return 1\n    return 0\n")
    _write(tmp_path, "src/util.py", "# helper\ndef g():\n    pass\n")
    _write(tmp_path, "README.md", "# Title\n")
    _write(tmp_path, "requirements.txt", "fastapi==0.111\n# comment\nredis>=5\n")
    _write(tmp_path, "package.json", json.dumps({"dependencies": {"react": "18"}, "devDependencies": {"vite": "5"}}))

    m = compute_metrics(str(tmp_path)).to_dict()

    assert m["file_count"] == 4
    assert m["total_lines"] > 0
    assert "Python" in m["languages"]
    assert m["avg_complexity"] >= 1
    assert m["dependencies"]["python"] == ["fastapi", "redis"]
    assert m["dependencies"]["node"] == ["react", "vite"]
    assert any(f["path"] == "src" for f in m["folder_summary"])
    assert 0 <= m["doc_coverage_pct"] <= 100


def test_compute_metrics_empty(tmp_path: Path):
    m = compute_metrics(str(tmp_path)).to_dict()
    assert m["file_count"] == 0
    assert m["languages"] == {}


def test_complexity_hotspots_ranked(tmp_path: Path):
    branchy = "def f():\n" + "".join(f"    if x{i}:\n        pass\n" for i in range(20))
    _write(tmp_path, "complex.py", branchy)
    _write(tmp_path, "simple.py", "x = 1\n")

    m = compute_metrics(str(tmp_path)).to_dict()
    assert m["complexity_hotspots"][0]["file_path"] == "complex.py"
    assert m["max_complexity"] >= 20

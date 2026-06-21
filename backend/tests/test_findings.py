"""Unit tests for the finding-based scan scoring helpers."""
from __future__ import annotations

from app.application.use_cases.analysis.findings import _counts, _score


def test_counts_tallies_by_severity_and_ignores_unknown():
    findings = [
        {"severity": "critical"},
        {"severity": "high"},
        {"severity": "high"},
        {"severity": "bogus"},
        {},
    ]
    counts = _counts(findings)
    assert counts["critical"] == 1
    assert counts["high"] == 2
    assert counts["medium"] == 0
    assert counts["info"] == 0


def test_score_is_100_with_no_findings():
    assert _score(_counts([])) == 100


def test_score_penalizes_by_severity_weight():
    counts = _counts([{"severity": "critical"}, {"severity": "low"}])
    # 100 - (25 + 3) = 72
    assert _score(counts) == 72


def test_score_never_negative():
    counts = _counts([{"severity": "critical"}] * 10)
    assert _score(counts) == 0

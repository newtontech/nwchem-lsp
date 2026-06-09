"""Validation accuracy testing framework for NWChem LSP.

Provides infrastructure for measuring and reporting detection accuracy
across categories: task conflicts, method conflicts, chemistry constraints,
and basis set issues.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .lint import NwchemLintProvider


@dataclass
class TestCase:
    """A single validation test case."""

    name: str
    category: str
    source: str
    expected_codes: List[str] = field(default_factory=list)
    expected_line: Optional[int] = None
    should_detect: bool = True

@dataclass
class TestResult:
    """Result of running a single test case."""

    name: str
    category: str
    detected: bool
    correct: bool
    expected_codes: List[str] = field(default_factory=list)
    actual_codes: List[str] = field(default_factory=list)

@dataclass
class AccuracyReport:
    """Aggregated accuracy report by category."""

    total: int = 0
    correct: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    accuracy: float = 0.0
    by_category: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "total": self.total,
            "correct": self.correct,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "accuracy": round(self.accuracy, 4),
            "by_category": self.by_category,
        }, indent=2)


class ValidationAccuracyFramework:
    """Framework for measuring validation detection accuracy."""

    def __init__(self, lint_provider: Optional[NwchemLintProvider] = None) -> None:
        self._lint = lint_provider or NwchemLintProvider()
        self._test_cases: List[TestCase] = []

    def add_test_case(self, case: TestCase) -> None:
        self._test_cases.append(case)

    def run_test(self, case: TestCase) -> TestResult:
        """Run a single test case against the lint provider."""
        diagnostics = self._lint.lint(case.source)
        actual_codes = [str(d.code) for d in diagnostics]
        detected = any(code in actual_codes for code in case.expected_codes) if case.expected_codes else len(diagnostics) > 0

        correct = detected == case.should_detect

        return TestResult(
            name=case.name,
            category=case.category,
            detected=detected,
            correct=correct,
            expected_codes=case.expected_codes,
            actual_codes=actual_codes,
        )

    def run_all(self) -> AccuracyReport:
        """Run all test cases and produce an accuracy report."""
        results = [self.run_test(c) for c in self._test_cases]

        by_category: Dict[str, Dict[str, Any]] = {}
        total_correct = 0
        total_fp = 0
        total_fn = 0

        for r in results:
            if r.category not in by_category:
                by_category[r.category] = {"total": 0, "correct": 0, "fp": 0, "fn": 0}
            cat = by_category[r.category]
            cat["total"] += 1

            if r.correct:
                cat["correct"] += 1
                total_correct += 1
            elif r.detected and not r.correct:
                cat["fp"] += 1
                total_fp += 1
            else:
                cat["fn"] += 1
                total_fn += 1

        for cat in by_category.values():
            cat["accuracy"] = round(cat["correct"] / cat["total"], 4) if cat["total"] > 0 else 0.0

        total = len(results)
        return AccuracyReport(
            total=total,
            correct=total_correct,
            false_positives=total_fp,
            false_negatives=total_fn,
            accuracy=round(total_correct / total, 4) if total > 0 else 0.0,
            by_category=by_category,
        )

    @property
    def test_count(self) -> int:
        return len(self._test_cases)

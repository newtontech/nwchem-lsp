"""Tests for the validation accuracy framework."""

import json
import pytest

from nwchem_lsp.features.validation_accuracy import (
    AccuracyReport,
    TestCase,
    TestResult,
    ValidationAccuracyFramework,
)


@pytest.fixture
def framework() -> ValidationAccuracyFramework:
    return ValidationAccuracyFramework()


class TestTestCase:
    def test_create(self):
        tc = TestCase(name="test1", category="tasks", source="task scf\n")
        assert tc.name == "test1"
        assert tc.should_detect is True


class TestAccuracyReport:
    def test_to_json(self):
        report = AccuracyReport(total=10, correct=9, accuracy=0.9)
        data = json.loads(report.to_json())
        assert data["total"] == 10
        assert data["accuracy"] == 0.9


class TestFramework:
    def test_empty(self, framework: ValidationAccuracyFramework):
        assert framework.test_count == 0
        report = framework.run_all()
        assert report.total == 0

    def test_add_and_run(self, framework: ValidationAccuracyFramework):
        framework.add_test_case(TestCase(
            name="basic", category="tasks", source="task scf\ntask dft\nend\n",
            expected_codes=["NW2001"]))
        assert framework.test_count == 1
        report = framework.run_all()
        assert report.total == 1

    def test_accuracy_report(self, framework: ValidationAccuracyFramework):
        framework.add_test_case(TestCase(
            name="good", category="tasks", source="task scf\n",
            expected_codes=[], should_detect=False))
        report = framework.run_all()
        assert report.total == 1
        assert "tasks" in report.by_category

    def test_category_breakdown(self, framework: ValidationAccuracyFramework):
        framework.add_test_case(TestCase(name="a", category="cat1", source="task scf\n"))
        framework.add_test_case(TestCase(name="b", category="cat2", source="task scf\n"))
        report = framework.run_all()
        assert "cat1" in report.by_category
        assert "cat2" in report.by_category

    def test_json_report(self, framework: ValidationAccuracyFramework):
        framework.add_test_case(TestCase(name="a", category="t", source="task scf\n"))
        report = framework.run_all()
        data = json.loads(report.to_json())
        assert "by_category" in data

"""Tests for regression harness."""

import json
import pytest

from nwchem_lsp.features.regression import (
    GoldenFixture,
    RegressionHarness,
    RegressionResult,
)


@pytest.fixture
def harness() -> RegressionHarness:
    return RegressionHarness()


class TestGoldenFixture:
    def test_create(self):
        f = GoldenFixture(name="test1", input_source="title test\n")
        assert f.name == "test1"
        assert f.expected_diagnostics == []


class TestRegressionHarness:
    def test_empty(self, harness: RegressionHarness):
        assert harness.fixture_count == 0
        assert harness.run_all() == []

    def test_add_fixture(self, harness: RegressionHarness):
        harness.add_fixture(GoldenFixture(name="basic", input_source="title test\n"))
        assert harness.fixture_count == 1
        assert "basic" in harness.fixture_names

    def test_run_fixture(self, harness: RegressionHarness):
        harness.add_fixture(GoldenFixture(
            name="basic", input_source="title test\n",
            expected_diagnostics=[]))
        result = harness.run_fixture("basic")
        assert isinstance(result, RegressionResult)
        assert result.name == "basic"

    def test_run_missing_fixture(self, harness: RegressionHarness):
        result = harness.run_fixture("nonexistent")
        assert not result.passed
        assert "not found" in result.mismatches[0]

    def test_run_all(self, harness: RegressionHarness):
        harness.add_fixture(GoldenFixture(name="a", input_source="title a\n"))
        harness.add_fixture(GoldenFixture(name="b", input_source="title b\n"))
        results = harness.run_all()
        assert len(results) == 2

    def test_snapshot_fixture(self, harness: RegressionHarness):
        output = harness.snapshot_fixture("test", "title test\n")
        data = json.loads(output)
        assert data["name"] == "test"
        assert "expected_diagnostics" in data

    def test_diagnostic_count_mismatch(self, harness: RegressionHarness):
        harness.add_fixture(GoldenFixture(
            name="mismatch", input_source="title test\n",
            expected_diagnostics=[{"line": 0, "message": "fake"}]))
        result = harness.run_fixture("mismatch")
        assert not result.passed
        assert any("count mismatch" in m for m in result.mismatches)

"""Tests for the NWChem test-runner / dry-run bridge."""

from __future__ import annotations

import json

import pytest

from lsprotocol.types import DiagnosticSeverity

from nwchem_lsp.features.test_runner import (
    TestRunnerConfig,
    TestRunnerProvider,
    parse_solver_output,
    solver_output_to_diagnostics,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def provider() -> TestRunnerProvider:
    """Provider with default (disabled) config."""
    return TestRunnerProvider()


@pytest.fixture
def enabled_provider() -> TestRunnerProvider:
    """Provider with enabled config but no real executable."""
    config = TestRunnerConfig(executable="/usr/bin/true", enabled=True)
    return TestRunnerProvider(config)


# ------------------------------------------------------------------
# TestRunnerConfig
# ------------------------------------------------------------------

class TestTestRunnerConfig:
    def test_default_disabled(self) -> None:
        config = TestRunnerConfig()
        assert not config.enabled
        assert config.executable == ""

    def test_validate_missing_executable(self) -> None:
        config = TestRunnerConfig(enabled=True, executable="")
        errors = config.validate()
        assert len(errors) == 1
        assert "not configured" in errors[0]

    def test_validate_negative_timeout(self) -> None:
        config = TestRunnerConfig(timeout=-1)
        errors = config.validate()
        assert any("positive" in e for e in errors)

    def test_validate_ok(self) -> None:
        config = TestRunnerConfig(executable="nwchem", enabled=True)
        errors = config.validate()
        assert len(errors) == 0


# ------------------------------------------------------------------
# Output parsing
# ------------------------------------------------------------------

class TestParseSolverOutput:
    def test_empty_output(self) -> None:
        result = parse_solver_output("")
        assert result.success
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_error_with_line_number(self) -> None:
        output = "  5: error: unknown keyword foo\n"
        result = parse_solver_output(output)
        assert not result.success
        assert len(result.errors) == 1
        assert result.errors[0]["line"] == 4  # 0-indexed
        assert "foo" in result.errors[0]["message"]

    def test_warning(self) -> None:
        output = "  3: warning: deprecated syntax\n"
        result = parse_solver_output(output)
        assert result.success  # warnings don't make it fail
        assert len(result.warnings) == 1
        assert "deprecated" in result.warnings[0]["message"]

    def test_runtime_error(self) -> None:
        output = "Runtime error: Unable to open file\n"
        result = parse_solver_output(output)
        assert not result.success
        assert len(result.errors) == 1
        assert "Unable to open" in result.errors[0]["message"]

    def test_input_error(self) -> None:
        output = "input error: invalid charge value\n"
        result = parse_solver_output(output)
        assert not result.success
        assert "invalid charge" in result.errors[0]["message"]

    def test_multiple_errors(self) -> None:
        output = "  1: error: missing section\n  5: error: bad value\n"
        result = parse_solver_output(output)
        assert len(result.errors) == 2


class TestSolverOutputToDiagnostics:
    def test_error_becomes_diagnostic(self) -> None:
        from nwchem_lsp.features.test_runner import SolverOutput
        output = SolverOutput(
            success=False,
            errors=[{"message": "test error", "line": 2, "source": "test"}],
        )
        diags = solver_output_to_diagnostics(output)
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.Error
        assert diags[0].range.start.line == 2
        assert diags[0].code == "NW9001"

    def test_warning_becomes_diagnostic(self) -> None:
        from nwchem_lsp.features.test_runner import SolverOutput
        output = SolverOutput(
            success=True,
            warnings=[{"message": "test warning", "line": 0, "source": "test"}],
        )
        diags = solver_output_to_diagnostics(output)
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.Warning
        assert diags[0].code == "NW9002"

    def test_empty_output_no_diagnostics(self) -> None:
        from nwchem_lsp.features.test_runner import SolverOutput
        output = SolverOutput()
        diags = solver_output_to_diagnostics(output)
        assert len(diags) == 0


# ------------------------------------------------------------------
# TestRunnerProvider
# ------------------------------------------------------------------

class TestTestRunnerProvider:
    def test_disabled_returns_info_diagnostic(self, provider: TestRunnerProvider) -> None:
        diags = provider.run_validation("start\n  task scf\nend\n")
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.Information
        assert "not enabled" in diags[0].message

    def test_no_executable_returns_warning(self) -> None:
        config = TestRunnerConfig(executable="", enabled=True)
        provider = TestRunnerProvider(config)
        diags = provider.run_validation("test")
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.Warning

    def test_missing_executable_returns_error(self) -> None:
        config = TestRunnerConfig(executable="/nonexistent/nwchem", enabled=True)
        provider = TestRunnerProvider(config)
        diags = provider.run_validation("test")
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.Error
        assert "not found" in diags[0].message

    def test_captured_output_parsing(self) -> None:
        provider = TestRunnerProvider()
        captured = "  3: error: bad input line\n"
        diags = provider.run_with_captured_output(captured)
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.Error
        assert diags[0].range.start.line == 2

    def test_captured_clean_output(self) -> None:
        provider = TestRunnerProvider()
        diags = provider.run_with_captured_output("All checks passed.\n")
        assert len(diags) == 0

    def test_config_snapshot(self) -> None:
        config = TestRunnerConfig(executable="nwchem", enabled=True, timeout=60.0)
        provider = TestRunnerProvider(config)
        snapshot = json.loads(provider.snapshot_config())
        assert snapshot["enabled"] is True
        assert snapshot["executable"] == "nwchem"
        assert snapshot["timeout"] == 60.0

    def test_validate_config(self) -> None:
        config = TestRunnerConfig(enabled=True, executable="")
        provider = TestRunnerProvider(config)
        errors = provider.validate_config()
        assert len(errors) > 0

    def test_config_setter(self) -> None:
        provider = TestRunnerProvider()
        new_config = TestRunnerConfig(executable="nwchem", enabled=True)
        provider.config = new_config
        assert provider.config.executable == "nwchem"
        assert provider.config.enabled is True

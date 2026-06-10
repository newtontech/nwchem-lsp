"""Tests for additional example files and lint fixtures.

Covers ECP, frequency, CCSD(T) examples plus additional lint fixtures.
"""

import pathlib

import pytest
from lsprotocol.types import DiagnosticSeverity

from nwchem_lsp.features.diagnostic import DiagnosticProvider
from nwchem_lsp.features.lint import NwchemLintProvider
from nwchem_lsp.parser.nwchem_parser import NwchemParser
from pygls.server import LanguageServer

EXAMPLES_DIR = pathlib.Path(__file__).parent.parent.parent / "examples"
FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "lint"


def load_example(name: str) -> str:
    return (EXAMPLES_DIR / name).read_text()


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


def codes(diagnostics):
    return {str(d.code) for d in diagnostics if d.code is not None}


@pytest.fixture
def server():
    return LanguageServer("test", "1.0")


@pytest.fixture
def diagnostic_provider(server):
    return DiagnosticProvider(server)


@pytest.fixture
def lint_provider():
    return NwchemLintProvider()


# ------------------------------------------------------------------
# ECP example
# ------------------------------------------------------------------

class TestECPExample:
    """Tests for the fe_scf_ecp.nw example."""

    def test_file_exists(self):
        assert (EXAMPLES_DIR / "fe_scf_ecp.nw").exists()

    def test_parse(self):
        text = load_example("fe_scf_ecp.nw")
        parser = NwchemParser(text)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "ecp" in sections
        assert "scf" in sections
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid, f"fe_scf_ecp.nw has syntax errors: {errors}"

    def test_no_diagnostic_errors(self, diagnostic_provider):
        text = load_example("fe_scf_ecp.nw")
        diags = diagnostic_provider.get_diagnostics(text)
        errors = [d for d in diags if d.severity == DiagnosticSeverity.Error]
        assert len(errors) == 0, f"fe_scf_ecp.nw errors: {[d.message for d in errors]}"

    def test_lint_clean(self, lint_provider):
        text = load_example("fe_scf_ecp.nw")
        diags = lint_provider.lint(text)
        errors = [d for d in diags if d.severity == DiagnosticSeverity.Error]
        assert len(errors) == 0, f"fe_scf_ecp.nw lint errors: {[d.message for d in errors]}"


# ------------------------------------------------------------------
# Frequency example
# ------------------------------------------------------------------

class TestFrequencyExample:
    """Tests for the h2o_freq.nw example."""

    def test_file_exists(self):
        assert (EXAMPLES_DIR / "h2o_freq.nw").exists()

    def test_parse(self):
        text = load_example("h2o_freq.nw")
        parser = NwchemParser(text)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "dft" in sections
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid

    def test_has_two_tasks(self):
        text = load_example("h2o_freq.nw")
        parser = NwchemParser(text)
        blocks = parser.parse()
        tasks = [b for b in blocks if b.name == "task"]
        assert len(tasks) == 2

    def test_no_diagnostic_errors(self, diagnostic_provider):
        text = load_example("h2o_freq.nw")
        diags = diagnostic_provider.get_diagnostics(text)
        errors = [d for d in diags if d.severity == DiagnosticSeverity.Error]
        assert len(errors) == 0, f"h2o_freq.nw errors: {[d.message for d in errors]}"


# ------------------------------------------------------------------
# CCSD(T) example
# ------------------------------------------------------------------

class TestCCSDExample:
    """Tests for the methane_ccsd.nw example."""

    def test_file_exists(self):
        assert (EXAMPLES_DIR / "methane_ccsd.nw").exists()

    def test_parse(self):
        text = load_example("methane_ccsd.nw")
        parser = NwchemParser(text)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "ccsd" in sections
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid

    def test_no_diagnostic_errors(self, diagnostic_provider):
        text = load_example("methane_ccsd.nw")
        diags = diagnostic_provider.get_diagnostics(text)
        errors = [d for d in diags if d.severity == DiagnosticSeverity.Error]
        assert len(errors) == 0, f"methane_ccsd.nw errors: {[d.message for d in errors]}"


# ------------------------------------------------------------------
# Additional lint fixtures
# ------------------------------------------------------------------

class TestAdditionalLintFixtures:
    """Tests for newly added lint fixture files."""

    def test_invalid_task_missing_operation_exists(self):
        assert (FIXTURES_DIR / "invalid_task_missing_operation.nw").exists()

    def test_loose_convergence_exists(self):
        assert (FIXTURES_DIR / "loose_convergence.nw").exists()

    def test_invalid_maxiter_string_exists(self):
        assert (FIXTURES_DIR / "invalid_maxiter_string.nw").exists()

    def test_task_missing_operation_no_crash(self, lint_provider):
        """Task with only theory should not crash the lint provider."""
        text = load_fixture("invalid_task_missing_operation.nw")
        diags = lint_provider.lint(text)
        assert isinstance(diags, list)

    def test_loose_convergence_hint(self, lint_provider):
        """NW3002: Unusually loose convergence threshold."""
        text = load_fixture("loose_convergence.nw")
        diags = lint_provider.lint(text)
        found = [d for d in diags if str(d.code) == "NW3002"]
        assert len(found) >= 1
        assert any("1e-2" in d.message or "loose" in d.message.lower() for d in found)

    def test_invalid_maxiter_string(self, lint_provider):
        """NW2003: Non-integer maxiter value."""
        text = load_fixture("invalid_maxiter_string.nw")
        diags = lint_provider.lint(text)
        found = [d for d in diags if str(d.code) == "NW2003"]
        assert len(found) >= 1
        assert any("abc" in d.message for d in found)

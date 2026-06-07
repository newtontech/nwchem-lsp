"""Tests for the NWChem validation framework."""

import pathlib

import pytest

from nwchem_lsp.features.validation import (
    NWChemValidationProvider,
    ValidationResult,
)
from nwchem_lsp.parser.nwchem_parser import NwchemParser


# Path to test fixtures
FIXTURES_DIR = pathlib.Path(__file__).parent / "validation"


@pytest.fixture
def provider():
    """Create a validation provider instance."""
    return NWChemValidationProvider()


def load_fixture(name: str) -> str:
    """Load a test fixture file by name."""
    filepath = FIXTURES_DIR / name
    return filepath.read_text()


def parse_and_validate(text: str, provider: NWChemValidationProvider):
    """Parse text and run validation, returning results."""
    parser = NwchemParser(text)
    sections = parser.sections
    return provider.validate(text, sections)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_to_diagnostic(self):
        """Test conversion to LSP Diagnostic."""
        result = ValidationResult(
            line=5,
            character=0,
            message="Test message",
            severity="Warning",
        )
        diagnostic = result.to_diagnostic()
        assert diagnostic.message == "Test message"
        assert diagnostic.range.start.line == 5
        assert diagnostic.range.start.character == 0

    def test_to_diagnostic_custom_end(self):
        """Test diagnostic with custom end character."""
        result = ValidationResult(
            line=2,
            character=3,
            message="Test",
            severity="Error",
            end_character=10,
        )
        diagnostic = result.to_diagnostic()
        assert diagnostic.range.end.character == 10


class TestTaskConflicts:
    """Tests for task conflict detection."""

    def test_duplicate_task_warning(self, provider):
        """Test that duplicate tasks produce a warning."""
        text = load_fixture("duplicate_task.nw")
        results = parse_and_validate(text, provider)

        task_warnings = [r for r in results if "Duplicate task" in r.message]
        assert len(task_warnings) >= 1

    def test_single_task_no_warning(self, provider):
        """Test that a single task does not produce a warning."""
        text = load_fixture("valid_input.nw")
        results = parse_and_validate(text, provider)

        task_warnings = [r for r in results if "Duplicate task" in r.message]
        assert len(task_warnings) == 0


class TestMethodConflicts:
    """Tests for method section conflict detection."""

    def test_scf_dft_conflict(self, provider):
        """Test that SCF and DFT sections together produce a warning."""
        text = load_fixture("scf_dft_conflict.nw")
        results = parse_and_validate(text, provider)

        method_warnings = [r for r in results if "SCF" in r.message and "DFT" in r.message]
        assert len(method_warnings) >= 1

    def test_mp2_ccsd_conflict(self, provider):
        """Test that MP2 and CCSD sections together produce a warning."""
        text = load_fixture("mp2_ccsd_conflict.nw")
        results = parse_and_validate(text, provider)

        method_warnings = [r for r in results if "MP2" in r.message and "CCSD" in r.message]
        assert len(method_warnings) >= 1

    def test_no_method_conflict_valid(self, provider):
        """Test that valid input with single method produces no method warnings."""
        text = load_fixture("valid_input.nw")
        results = parse_and_validate(text, provider)

        method_warnings = [
            r
            for r in results
            if any(
                kw in r.message
                for kw in ("SCF", "DFT", "MP2", "CCSD", "mutually exclusive")
            )
        ]
        assert len(method_warnings) == 0


class TestTaskSectionConflicts:
    """Tests for task theory vs section conflicts."""

    def test_task_dft_with_scf_section(self, provider):
        """Test warning when task uses DFT but SCF section is present."""
        text = load_fixture("task_section_conflict.nw")
        results = parse_and_validate(text, provider)

        conflict_warnings = [
            r for r in results if "Task uses DFT" in r.message or "SCF section" in r.message
        ]
        assert len(conflict_warnings) >= 1


class TestBasisSetIssues:
    """Tests for basis set issue detection."""

    def test_duplicate_basis_warning(self, provider):
        """Test that duplicate basis definitions produce a warning."""
        text = load_fixture("duplicate_basis.nw")
        results = parse_and_validate(text, provider)

        basis_warnings = [r for r in results if "Duplicate basis" in r.message]
        assert len(basis_warnings) >= 1

    def test_no_duplicate_basis_valid(self, provider):
        """Test that valid input with unique basis definitions produces no basis warnings."""
        text = load_fixture("valid_input.nw")
        results = parse_and_validate(text, provider)

        basis_warnings = [r for r in results if "Duplicate basis" in r.message]
        assert len(basis_warnings) == 0


class TestChargeMultiplicity:
    """Tests for charge/multiplicity validation."""

    def test_multiple_charge_warning(self, provider):
        """Test that multiple charge directives produce a warning."""
        text = load_fixture("multiple_charge.nw")
        results = parse_and_validate(text, provider)

        charge_warnings = [r for r in results if "Multiple charge" in r.message]
        assert len(charge_warnings) >= 1

    def test_single_charge_no_warning(self, provider):
        """Test that single charge directive produces no warning."""
        text = load_fixture("valid_input.nw")
        results = parse_and_validate(text, provider)

        charge_warnings = [r for r in results if "Multiple charge" in r.message]
        assert len(charge_warnings) == 0


class TestValidationProvider:
    """Integration tests for NWChemValidationProvider."""

    def test_validate_to_diagnostics(self, provider):
        """Test that validate_to_diagnostics returns LSP Diagnostic objects."""
        text = load_fixture("duplicate_task.nw")
        parser = NwchemParser(text)
        diagnostics = provider.validate_to_diagnostics(text, parser.sections)

        from lsprotocol.types import Diagnostic

        assert all(isinstance(d, Diagnostic) for d in diagnostics)
        assert len(diagnostics) > 0

    def test_valid_input_no_errors(self, provider):
        """Test that valid input produces no validation errors."""
        text = load_fixture("valid_input.nw")
        results = parse_and_validate(text, provider)

        # Valid input should have no critical validation issues
        # (informational warnings about charge/multiplicity are ok)
        error_results = [
            r
            for r in results
            if r.severity in ("Error", "error", 1)  # DiagnosticSeverity.Error = 1
        ]
        assert len(error_results) == 0

    def test_empty_sections(self, provider):
        """Test validation with empty sections dict."""
        text = "title test\n"
        parser = NwchemParser(text)
        results = provider.validate(text, parser.sections)
        assert isinstance(results, list)

    def test_empty_text(self, provider):
        """Test validation with empty text."""
        text = ""
        parser = NwchemParser(text)
        results = provider.validate(text, parser.sections)
        assert isinstance(results, list)


class TestValidationFixtures:
    """Test that all fixture files exist and are loadable."""

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "duplicate_task.nw",
            "scf_dft_conflict.nw",
            "mp2_ccsd_conflict.nw",
            "duplicate_basis.nw",
            "multiple_charge.nw",
            "valid_input.nw",
            "task_section_conflict.nw",
        ],
    )
    def test_fixture_exists(self, fixture_name):
        """Test that each fixture file exists."""
        filepath = FIXTURES_DIR / fixture_name
        assert filepath.exists(), f"Fixture file {fixture_name} not found"

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "duplicate_task.nw",
            "scf_dft_conflict.nw",
            "mp2_ccsd_conflict.nw",
            "duplicate_basis.nw",
            "multiple_charge.nw",
            "valid_input.nw",
            "task_section_conflict.nw",
        ],
    )
    def test_fixture_loadable(self, fixture_name):
        """Test that each fixture file can be loaded."""
        content = load_fixture(fixture_name)
        assert len(content) > 0
        assert "geometry" in content.lower()
        assert "basis" in content.lower()
        assert "task" in content.lower()

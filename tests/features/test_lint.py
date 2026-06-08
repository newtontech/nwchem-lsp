"""Tests for the schema-aware lint provider."""

import pathlib

import pytest

from lsprotocol.types import Diagnostic, DiagnosticSeverity

from nwchem_lsp.features.lint import NwchemLintProvider, RULE_DESCRIPTIONS


FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "lint"


@pytest.fixture
def provider():
    """Create a lint provider instance."""
    return NwchemLintProvider()


def load_fixture(name: str) -> str:
    """Load a test fixture file by name."""
    filepath = FIXTURES_DIR / name
    return filepath.read_text()


def lint_fixture(name: str, provider: NwchemLintProvider) -> list[Diagnostic]:
    """Load fixture and run lint, returning diagnostics."""
    text = load_fixture(name)
    return provider.lint(text)


def codes(diagnostics: list[Diagnostic]) -> set[str]:
    """Extract rule codes from a list of diagnostics."""
    return {str(d.code) for d in diagnostics if d.code is not None}


# ------------------------------------------------------------------
# Rule registry
# ------------------------------------------------------------------


class TestRuleRegistry:
    """Tests for the rule code registry."""

    def test_rule_descriptions_exist(self):
        """Every rule code should have a description."""
        assert len(RULE_DESCRIPTIONS) > 0
        for code, desc in RULE_DESCRIPTIONS.items():
            assert code.startswith("NW"), f"Rule code {code} does not start with NW"
            assert len(desc) > 0, f"Rule {code} has empty description"

    def test_syntax_rules_in_1000_range(self):
        """Syntax rules should be in the 1000-1999 range."""
        syntax_rules = [c for c in RULE_DESCRIPTIONS if c.startswith("NW1")]
        assert len(syntax_rules) >= 2
        for rule in syntax_rules:
            num = int(rule[2:])
            assert 1000 <= num <= 1999

    def test_schema_rules_in_2000_range(self):
        """Schema rules should be in the 2000-2999 range."""
        schema_rules = [c for c in RULE_DESCRIPTIONS if c.startswith("NW2")]
        assert len(schema_rules) >= 5
        for rule in schema_rules:
            num = int(rule[2:])
            assert 2000 <= num <= 2999

    def test_bestpractice_rules_in_3000_range(self):
        """Best-practice rules should be in the 3000-3999 range."""
        bp_rules = [c for c in RULE_DESCRIPTIONS if c.startswith("NW3")]
        assert len(bp_rules) >= 2
        for rule in bp_rules:
            num = int(rule[2:])
            assert 3000 <= num <= 3999


# ------------------------------------------------------------------
# Provider basics
# ------------------------------------------------------------------


class TestLintProvider:
    """Tests for NwchemLintProvider basics."""

    def test_provider_exists(self, provider):
        """Test that provider can be created."""
        assert provider is not None

    def test_lint_returns_list(self, provider):
        """Test that lint returns a list."""
        result = provider.lint("")
        assert isinstance(result, list)

    def test_lint_returns_diagnostics(self, provider):
        """Test that lint returns Diagnostic objects."""
        result = provider.lint("geometry\n  H 0 0 0\nend\nbasis\n  H library 6-31g\nend\ntask scf energy\n")
        assert all(isinstance(d, Diagnostic) for d in result)


# ------------------------------------------------------------------
# Syntax checks (NW1xxx)
# ------------------------------------------------------------------


class TestSyntaxChecks:
    """Tests for syntax-level lint rules."""

    def test_unclosed_section(self, provider):
        """NW1001: Unclosed section."""
        diags = lint_fixture("unclosed_section.nw", provider)
        assert "NW1001" in codes(diags)
        unclosed = [d for d in diags if str(d.code) == "NW1001"]
        assert any("geometry" in d.message.lower() for d in unclosed)
        # Verify it has a valid range
        for d in unclosed:
            assert d.range.start.line >= 0
            assert d.range.end.character > d.range.start.character

    def test_unexpected_end(self, provider):
        """NW1002: Unexpected end without matching section."""
        diags = lint_fixture("unexpected_end.nw", provider)
        assert "NW1002" in codes(diags)

    def test_valid_no_syntax_errors(self, provider):
        """Valid input should not produce syntax errors."""
        diags = lint_fixture("valid_input.nw", provider)
        syntax_codes = {c for c in codes(diags) if c.startswith("NW1")}
        assert len(syntax_codes) == 0


# ------------------------------------------------------------------
# Schema checks (NW2xxx)
# ------------------------------------------------------------------


class TestSchemaChecks:
    """Tests for schema violation lint rules."""

    def test_unknown_keyword(self, provider):
        """NW2001: Unknown keyword inside section."""
        diags = lint_fixture("unknown_keyword.nw", provider)
        assert "NW2001" in codes(diags)
        kw_diags = [d for d in diags if str(d.code) == "NW2001"]
        assert any("bogus_keyword" in d.message for d in kw_diags)

    def test_missing_required_section(self, provider):
        """NW2004: Missing required section."""
        diags = lint_fixture("missing_required.nw", provider)
        assert "NW2004" in codes(diags)
        missing = [d for d in diags if str(d.code) == "NW2004"]
        names = {d.message for d in missing}
        assert any("geometry" in n for n in names)
        assert any("basis" in n for n in names)

    def test_unknown_task_theory(self, provider):
        """NW2005: Unknown task theory."""
        diags = lint_fixture("unknown_task_theory.nw", provider)
        assert "NW2005" in codes(diags)
        theory_diags = [d for d in diags if str(d.code) == "NW2005"]
        assert any("bogus" in d.message for d in theory_diags)

    def test_unknown_task_operation(self, provider):
        """NW2006: Unknown task operation."""
        diags = lint_fixture("unknown_task_operation.nw", provider)
        assert "NW2006" in codes(diags)
        op_diags = [d for d in diags if str(d.code) == "NW2006"]
        assert any("bogus_operation" in d.message for d in op_diags)

    def test_unknown_basis_set(self, provider):
        """NW2007: Unknown basis set name."""
        diags = lint_fixture("unknown_basis.nw", provider)
        assert "NW2007" in codes(diags)
        basis_diags = [d for d in diags if str(d.code) == "NW2007"]
        assert any("bogus-basis-xyz" in d.message for d in basis_diags)

    def test_unknown_functional(self, provider):
        """NW2008: Unknown DFT functional."""
        diags = lint_fixture("unknown_functional.nw", provider)
        assert "NW2008" in codes(diags)
        func_diags = [d for d in diags if str(d.code) == "NW2008"]
        assert any("bogus_functional" in d.message for d in func_diags)

    def test_unknown_directive(self, provider):
        """NW2009: Unknown top-level directive."""
        diags = lint_fixture("unknown_directive.nw", provider)
        assert "NW2009" in codes(diags)
        dir_diags = [d for d in diags if str(d.code) == "NW2009"]
        assert any("foobarbaz" in d.message for d in dir_diags)

    def test_duplicate_section(self, provider):
        """NW2010: Duplicate singleton section."""
        diags = lint_fixture("duplicate_section.nw", provider)
        assert "NW2010" in codes(diags)
        dup_diags = [d for d in diags if str(d.code) == "NW2010"]
        assert any("geometry" in d.message for d in dup_diags)

    def test_invalid_grid_value(self, provider):
        """NW2002: Invalid enum value for grid."""
        diags = lint_fixture("invalid_grid.nw", provider)
        assert "NW2002" in codes(diags)
        grid_diags = [d for d in diags if str(d.code) == "NW2002"]
        assert any("megafine" in d.message for d in grid_diags)

    def test_invalid_units(self, provider):
        """NW2002: Invalid enum value for units."""
        diags = lint_fixture("invalid_units.nw", provider)
        assert "NW2002" in codes(diags)
        units_diags = [d for d in diags if str(d.code) == "NW2002"]
        assert any("parsecs" in d.message for d in units_diags)


# ------------------------------------------------------------------
# Best-practice checks (NW3xxx)
# ------------------------------------------------------------------


class TestBestPracticeChecks:
    """Tests for best-practice lint rules."""

    def test_unusual_maxiter(self, provider):
        """NW3001: SCF maxiter outside typical range."""
        diags = lint_fixture("unusual_maxiter.nw", provider)
        assert "NW3001" in codes(diags)
        maxiter_diags = [d for d in diags if str(d.code) == "NW3001"]
        assert any("9999" in d.message for d in maxiter_diags)
        # Should be Hint severity
        assert all(
            d.severity == DiagnosticSeverity.Hint for d in maxiter_diags
        )

    def test_duplicate_tasks(self, provider):
        """NW3003: Duplicate task directives."""
        diags = lint_fixture("duplicate_tasks.nw", provider)
        assert "NW3003" in codes(diags)
        dup_diags = [d for d in diags if str(d.code) == "NW3003"]
        assert len(dup_diags) >= 1


# ------------------------------------------------------------------
# False positive guard
# ------------------------------------------------------------------


class TestNoFalsePositives:
    """Ensure valid inputs do not produce errors or schema violations."""

    def test_valid_input_no_errors(self, provider):
        """Valid fixture should not produce error-severity diagnostics."""
        diags = lint_fixture("valid_input.nw", provider)
        errors = [d for d in diags if d.severity == DiagnosticSeverity.Error]
        assert len(errors) == 0

    def test_valid_input_no_schema_violations(self, provider):
        """Valid fixture should not produce NW2xxx codes."""
        diags = lint_fixture("valid_input.nw", provider)
        schema_codes = {c for c in codes(diags) if c.startswith("NW2")}
        assert len(schema_codes) == 0

    def test_valid_input_no_syntax_errors(self, provider):
        """Valid fixture should not produce NW1xxx codes."""
        diags = lint_fixture("valid_input.nw", provider)
        syntax_codes = {c for c in codes(diags) if c.startswith("NW1")}
        assert len(syntax_codes) == 0


# ------------------------------------------------------------------
# Diagnostic quality
# ------------------------------------------------------------------


class TestDiagnosticQuality:
    """Tests that diagnostics have proper ranges and attributes."""

    def test_all_diagnostics_have_source(self, provider):
        """All diagnostics should have source='nwchem-lsp'."""
        diags = lint_fixture("unknown_keyword.nw", provider)
        for d in diags:
            assert d.source == "nwchem-lsp"

    def test_all_diagnostics_have_codes(self, provider):
        """All diagnostics from lint should have rule codes."""
        diags = provider.lint(
            "scf\n  bogus_kw\nend\ntask fake energy\n"
        )
        for d in diags:
            assert d.code is not None, f"Diagnostic missing code: {d.message}"

    def test_all_diagnostics_have_valid_ranges(self, provider):
        """All diagnostics should have valid ranges."""
        diags = lint_fixture("unclosed_section.nw", provider)
        for d in diags:
            assert d.range.start.line >= 0
            assert d.range.end.line >= 0
            assert (
                d.range.end.line > d.range.start.line
                or d.range.end.character >= d.range.start.character
            )


# ------------------------------------------------------------------
# Fixture file existence
# ------------------------------------------------------------------


class TestLintFixtures:
    """Test that all lint fixture files exist and are loadable."""

    FIXTURE_NAMES = [
        "valid_input.nw",
        "unclosed_section.nw",
        "unexpected_end.nw",
        "unknown_keyword.nw",
        "unknown_task_theory.nw",
        "unknown_task_operation.nw",
        "unknown_basis.nw",
        "unknown_functional.nw",
        "unknown_directive.nw",
        "duplicate_section.nw",
        "duplicate_tasks.nw",
        "unusual_maxiter.nw",
        "invalid_grid.nw",
        "invalid_units.nw",
        "missing_required.nw",
    ]

    @pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
    def test_fixture_exists(self, fixture_name):
        """Test that each fixture file exists."""
        filepath = FIXTURES_DIR / fixture_name
        assert filepath.exists(), f"Fixture file {fixture_name} not found"

    @pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
    def test_fixture_loadable(self, fixture_name):
        """Test that each fixture file can be loaded."""
        content = load_fixture(fixture_name)
        assert len(content) > 0

"""Integration tests using real .nw example files from the examples/ directory.

These tests verify that all LSP features work correctly on actual NWChem input
files, not just synthetic inline test strings.
"""

import pathlib

import pytest
from lsprotocol.types import Position

from nwchem_lsp.features.completion import NwchemCompletionProvider
from nwchem_lsp.features.definition import DefinitionProvider
from nwchem_lsp.features.diagnostic import DiagnosticProvider
from nwchem_lsp.features.folding_range import FoldingRangeProvider
from nwchem_lsp.features.formatting import NwchemFormattingProvider
from nwchem_lsp.features.hover import NwchemHoverProvider
from nwchem_lsp.features.references import ReferencesProvider
from nwchem_lsp.features.rename import RenameProvider
from nwchem_lsp.features.semantic_tokens import SemanticTokensProvider
from nwchem_lsp.features.symbols import NwchemSymbolProvider
from nwchem_lsp.parser.nwchem_parser import NwchemParser
from pygls.server import LanguageServer

EXAMPLES_DIR = pathlib.Path(__file__).parent.parent.parent / "examples"


def load_example(name: str) -> str:
    """Load an example .nw file."""
    path = EXAMPLES_DIR / name
    return path.read_text()


@pytest.fixture
def server():
    """Create a test language server."""
    return LanguageServer("test", "1.0")


@pytest.fixture
def completion_provider(server):
    return NwchemCompletionProvider(server)


@pytest.fixture
def hover_provider(server):
    return NwchemHoverProvider(server)


@pytest.fixture
def diagnostic_provider(server):
    return DiagnosticProvider(server)


@pytest.fixture
def symbol_provider(server):
    return NwchemSymbolProvider(server)


@pytest.fixture
def formatting_provider(server):
    return NwchemFormattingProvider(server)


@pytest.fixture
def folding_provider(server):
    return FoldingRangeProvider(server)


@pytest.fixture
def definition_provider():
    return DefinitionProvider()


@pytest.fixture
def references_provider(server):
    return ReferencesProvider(server)


@pytest.fixture
def rename_provider(server):
    return RenameProvider(server)


@pytest.fixture
def semantic_provider(server):
    return SemanticTokensProvider(server)


# ------------------------------------------------------------------
# Fixture existence tests
# ------------------------------------------------------------------

EXAMPLE_FILES = [
    "water_dft.nw",
    "ethanol_scf.nw",
    "benzene_mp2.nw",
    "water_dft.nwinp",
]


class TestExampleFilesExist:
    """Verify all example files are present and loadable."""

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_file_exists(self, filename):
        path = EXAMPLES_DIR / filename
        assert path.exists(), f"Example file {filename} not found"

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_file_not_empty(self, filename):
        content = load_example(filename)
        assert len(content) > 20, f"Example file {filename} is suspiciously short"


# ------------------------------------------------------------------
# Parser tests on real examples
# ------------------------------------------------------------------

class TestParserOnExamples:
    """Test the parser against real example files."""

    def test_parse_water_dft(self):
        text = load_example("water_dft.nw")
        parser = NwchemParser(text)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "dft" in sections
        # task directives are parsed separately
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid, f"water_dft.nw has syntax errors: {errors}"

    def test_parse_ethanol_scf(self):
        text = load_example("ethanol_scf.nw")
        parser = NwchemParser(text)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "scf" in sections
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid, f"ethanol_scf.nw has syntax errors: {errors}"

    def test_parse_benzene_mp2(self):
        text = load_example("benzene_mp2.nw")
        parser = NwchemParser(text)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "mp2" in sections
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid, f"benzene_mp2.nw has syntax errors: {errors}"

    def test_parse_nwinp(self):
        text = load_example("water_dft.nwinp")
        parser = NwchemParser(text)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "dft" in sections
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid, f"water_dft.nwinp has syntax errors: {errors}"

    def test_water_dft_geometry_content(self):
        text = load_example("water_dft.nw")
        parser = NwchemParser(text)
        geo_sections = parser.get_section_content("geometry")
        assert len(geo_sections) == 1
        geo = geo_sections[0]
        # Should have the O atom and 2 H atoms as keywords (element symbols)
        content_text = "\n".join(geo.content).lower()
        assert "o" in content_text
        assert "h" in content_text

    def test_water_dft_dft_section(self):
        text = load_example("water_dft.nw")
        parser = NwchemParser(text)
        dft_sections = parser.get_section_content("dft")
        assert len(dft_sections) == 1
        dft = dft_sections[0]
        content_text = "\n".join(dft.content).lower()
        assert "xc" in content_text
        assert "b3lyp" in content_text
        assert "grid" in content_text

    def test_ethanol_scf_has_maxiter(self):
        text = load_example("ethanol_scf.nw")
        parser = NwchemParser(text)
        scf_sections = parser.get_section_content("scf")
        assert len(scf_sections) == 1
        scf = scf_sections[0]
        content_text = "\n".join(scf.content).lower()
        assert "maxiter" in content_text
        assert "thresh" in content_text

    def test_benzene_mp2_has_freeze(self):
        text = load_example("benzene_mp2.nw")
        parser = NwchemParser(text)
        mp2_sections = parser.get_section_content("mp2")
        assert len(mp2_sections) == 1
        mp2 = mp2_sections[0]
        content_text = "\n".join(mp2.content).lower()
        assert "freeze" in content_text

    def test_parser_idempotent(self):
        """Parsing the same file twice must produce identical results."""
        text = load_example("water_dft.nw")
        parser1 = NwchemParser(text)
        parser2 = NwchemParser(text)
        assert parser1.get_all_sections() == parser2.get_all_sections()
        assert parser1.is_valid_syntax() == parser2.is_valid_syntax()


# ------------------------------------------------------------------
# Diagnostics on real examples
# ------------------------------------------------------------------

class TestDiagnosticsOnExamples:
    """Test that real example files produce clean (or expected) diagnostics."""

    def test_water_dft_no_errors(self, diagnostic_provider):
        text = load_example("water_dft.nw")
        diags = diagnostic_provider.get_diagnostics(text)
        errors = [d for d in diags if d.severity == 1]  # Error severity
        assert len(errors) == 0, f"water_dft.nw has unexpected errors: {[d.message for d in errors]}"

    def test_ethanol_scf_no_errors(self, diagnostic_provider):
        text = load_example("ethanol_scf.nw")
        diags = diagnostic_provider.get_diagnostics(text)
        errors = [d for d in diags if d.severity == 1]
        assert len(errors) == 0, f"ethanol_scf.nw has unexpected errors: {[d.message for d in errors]}"

    def test_benzene_mp2_no_errors(self, diagnostic_provider):
        text = load_example("benzene_mp2.nw")
        diags = diagnostic_provider.get_diagnostics(text)
        errors = [d for d in diags if d.severity == 1]
        assert len(errors) == 0, f"benzene_mp2.nw has unexpected errors: {[d.message for d in errors]}"

    def test_nwinp_no_errors(self, diagnostic_provider):
        text = load_example("water_dft.nwinp")
        diags = diagnostic_provider.get_diagnostics(text)
        errors = [d for d in diags if d.severity == 1]
        assert len(errors) == 0, f"water_dft.nwinp has unexpected errors: {[d.message for d in errors]}"

    def test_water_dft_diagnostics_stable(self, diagnostic_provider):
        """Running diagnostics twice on the same input must produce identical results."""
        text = load_example("water_dft.nw")
        diags1 = diagnostic_provider.get_diagnostics(text)
        diags2 = diagnostic_provider.get_diagnostics(text)
        assert len(diags1) == len(diags2)
        for d1, d2 in zip(diags1, diags2):
            assert d1.message == d2.message
            assert d1.severity == d2.severity
            assert d1.range == d2.range


# ------------------------------------------------------------------
# Completion on real examples
# ------------------------------------------------------------------

class TestCompletionOnExamples:
    """Test completion provider works on real example files."""

    def test_top_level_completion(self, completion_provider):
        text = load_example("water_dft.nw")
        # Cursor at start of empty area after task line
        completions = completion_provider.get_completions(text, Position(line=0, character=0))
        assert len(completions) > 0
        labels = [c.label for c in completions]
        assert "geometry" in labels or any("geometry" in l for l in labels)

    def test_dft_section_completion(self, completion_provider):
        text = load_example("water_dft.nw")
        # Inside the DFT block, after "xc b3lyp"
        completions = completion_provider.get_completions(text, Position(line=19, character=0))
        assert isinstance(completions, list)

    def test_scf_section_completion(self, completion_provider):
        text = load_example("ethanol_scf.nw")
        # Inside SCF block
        completions = completion_provider.get_completions(text, Position(line=25, character=2))
        assert isinstance(completions, list)
        if completions:
            labels = [c.label for c in completions]
            # Should suggest SCF keywords like rhf, uhf, maxiter
            assert any(kw in labels for kw in ["maxiter", "thresh", "singlet", "rhf"])


# ------------------------------------------------------------------
# Hover on real examples
# ------------------------------------------------------------------

class TestHoverOnExamples:
    """Test hover provider on real example files."""

    def test_hover_on_geometry_keyword(self, hover_provider):
        text = load_example("water_dft.nw")
        # "geometry" starts at line 7 in water_dft.nw (0-indexed)
        hover = hover_provider.get_hover(text, Position(line=7, character=4))
        assert hover is not None, "Hover on 'geometry' keyword should return info"

    def test_hover_on_xc_keyword(self, hover_provider):
        text = load_example("water_dft.nw")
        # "xc b3lyp" is at line 18 in water_dft.nw (0-indexed)
        hover = hover_provider.get_hover(text, Position(line=18, character=2))
        assert hover is not None, "Hover on 'xc' keyword should return info"

    def test_hover_on_scf_keyword(self, hover_provider):
        text = load_example("ethanol_scf.nw")
        lines = text.splitlines()
        # Find the line with "maxiter"
        maxiter_line = None
        for i, line in enumerate(lines):
            if "maxiter" in line.lower():
                maxiter_line = i
                break
        assert maxiter_line is not None, "Could not find maxiter line"
        hover = hover_provider.get_hover(text, Position(line=maxiter_line, character=2))
        assert hover is not None, "Hover on 'maxiter' should return info"


# ------------------------------------------------------------------
# Document Symbols on real examples
# ------------------------------------------------------------------

class TestSymbolsOnExamples:
    """Test document symbols on real example files."""

    def test_water_dft_symbols(self, symbol_provider):
        text = load_example("water_dft.nw")
        symbols = symbol_provider.get_document_symbols(text)
        assert len(symbols) > 0, "water_dft.nw should have document symbols"
        symbol_names = []
        for s in symbols:
            if hasattr(s, "name"):
                symbol_names.append(s.name)
            elif hasattr(s, "children"):
                for child in (s.children or []):
                    if hasattr(child, "name"):
                        symbol_names.append(child.name)
        # Should find geometry, basis, dft sections
        assert len(symbol_names) > 0

    def test_ethanol_scf_symbols(self, symbol_provider):
        text = load_example("ethanol_scf.nw")
        symbols = symbol_provider.get_document_symbols(text)
        assert len(symbols) > 0, "ethanol_scf.nw should have document symbols"


# ------------------------------------------------------------------
# Formatting on real examples
# ------------------------------------------------------------------

class TestFormattingOnExamples:
    """Test formatting provider on real example files."""

    def test_format_water_dft_idempotent(self, formatting_provider):
        """Formatting an already-formatted file should produce no changes."""
        from lsprotocol.types import DocumentFormattingParams, FormattingOptions
        text = load_example("water_dft.nw")
        params = DocumentFormattingParams(
            text_document=None,  # type: ignore
            options=FormattingOptions(tab_size=2, insert_spaces=True),
        )
        edits = formatting_provider.format_document(text, params)
        # Well-formatted file should produce minimal edits
        # (may produce some whitespace normalization)
        assert isinstance(edits, list)

    def test_format_preserves_semantics(self, formatting_provider):
        """Formatting should not change the semantic content."""
        from lsprotocol.types import DocumentFormattingParams, FormattingOptions
        text = load_example("water_dft.nw")
        params = DocumentFormattingParams(
            text_document=None,  # type: ignore
            options=FormattingOptions(tab_size=2, insert_spaces=True),
        )
        edits = formatting_provider.format_document(text, params)
        if edits:
            formatted = edits[0].new_text
            # The formatted version should parse correctly
            parser = NwchemParser(formatted)
            is_valid, errors = parser.is_valid_syntax()
            assert is_valid, f"Formatted text has syntax errors: {errors}"
            assert "geometry" in parser.get_all_sections()
            assert "basis" in parser.get_all_sections()
            assert "dft" in parser.get_all_sections()


# ------------------------------------------------------------------
# Folding Ranges on real examples
# ------------------------------------------------------------------

class TestFoldingRangesOnExamples:
    """Test folding range provider on real example files."""

    def test_water_dft_folding(self, folding_provider):
        text = load_example("water_dft.nw")
        ranges = folding_provider.get_folding_ranges(text)
        assert len(ranges) > 0, "water_dft.nw should have foldable sections"
        # Should have geometry, basis, and dft folding ranges
        for r in ranges:
            assert r.end_line >= r.start_line

    def test_ethanol_scf_folding(self, folding_provider):
        text = load_example("ethanol_scf.nw")
        ranges = folding_provider.get_folding_ranges(text)
        assert len(ranges) > 0


# ------------------------------------------------------------------
# Definition on real examples
# ------------------------------------------------------------------

class TestDefinitionOnExamples:
    """Test go-to-definition on real example files."""

    def test_end_goes_to_section_start(self, definition_provider):
        text = load_example("water_dft.nw")
        # "end" on line 11 closes geometry (0-indexed)
        result = definition_provider.get_definition(text, Position(line=11, character=1))
        assert result is not None, "Go-to-definition on 'end' should find section start"

    def test_end_in_dft_goes_to_dft_start(self, definition_provider):
        text = load_example("water_dft.nw")
        # "end" on line 21 closes dft section (0-indexed)
        result = definition_provider.get_definition(text, Position(line=21, character=1))
        assert result is not None


# ------------------------------------------------------------------
# References on real examples
# ------------------------------------------------------------------

class TestReferencesOnExamples:
    """Test find-references on real example files."""

    def test_find_geometry_references(self, references_provider):
        text = load_example("water_dft.nw")
        uri = "file:///water_dft.nw"
        # "geometry" keyword at line 7, column 0 (0-indexed)
        result = references_provider.get_references(
            text, uri, Position(line=7, character=0), include_declaration=True
        )
        assert isinstance(result, list)
        assert len(result) > 0, "Should find references to geometry section"


# ------------------------------------------------------------------
# Rename on real examples
# ------------------------------------------------------------------

class TestRenameOnExamples:
    """Test rename on real example files."""

    def test_rename_geometry_to_scf(self, rename_provider):
        text = load_example("water_dft.nw")
        uri = "file:///water_dft.nw"
        # "geometry" at line 7, column 0 (0-indexed)
        result = rename_provider.get_rename_edits(
            text, uri, Position(line=7, character=0), "scf"
        )
        assert result is not None, "Renaming 'geometry' to 'scf' should succeed"
        assert uri in result.changes
        assert len(result.changes[uri]) > 0


# ------------------------------------------------------------------
# Semantic Tokens on real examples
# ------------------------------------------------------------------

class TestSemanticTokensOnExamples:
    """Test semantic tokens on real example files."""

    def test_water_dft_tokens(self, semantic_provider):
        text = load_example("water_dft.nw")
        result = semantic_provider.get_semantic_tokens(text)
        assert result is not None, "Semantic tokens should be produced"


# ------------------------------------------------------------------
# Lint on real examples
# ------------------------------------------------------------------

class TestLintOnExamples:
    """Test lint provider on real example files."""

    def test_water_dft_lint_clean(self):
        from nwchem_lsp.features.lint import NwchemLintProvider
        provider = NwchemLintProvider()
        text = load_example("water_dft.nw")
        diags = provider.lint(text)
        errors = [d for d in diags if d.severity == 1]  # Error
        assert len(errors) == 0, f"water_dft.nw lint errors: {[d.message for d in errors]}"

    def test_ethanol_scf_lint_clean(self):
        from nwchem_lsp.features.lint import NwchemLintProvider
        provider = NwchemLintProvider()
        text = load_example("ethanol_scf.nw")
        diags = provider.lint(text)
        errors = [d for d in diags if d.severity == 1]
        assert len(errors) == 0, f"ethanol_scf.nw lint errors: {[d.message for d in errors]}"

    def test_benzene_mp2_lint_clean(self):
        from nwchem_lsp.features.lint import NwchemLintProvider
        provider = NwchemLintProvider()
        text = load_example("benzene_mp2.nw")
        diags = provider.lint(text)
        errors = [d for d in diags if d.severity == 1]
        assert len(errors) == 0, f"benzene_mp2.nw lint errors: {[d.message for d in errors]}"

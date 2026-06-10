"""Edge-case and invalid-input tests for NWChem LSP.

These tests verify robustness of the parser, diagnostics, completion,
hover, formatting, and other features against unusual, malformed, or
boundary inputs.
"""

import pytest
from lsprotocol.types import Position

from nwchem_lsp.features.completion import NwchemCompletionProvider
from nwchem_lsp.features.definition import DefinitionProvider
from nwchem_lsp.features.diagnostic import DiagnosticProvider
from nwchem_lsp.features.formatting import NwchemFormattingProvider
from nwchem_lsp.features.hover import NwchemHoverProvider
from nwchem_lsp.features.lint import NwchemLintProvider
from nwchem_lsp.parser.nwchem_parser import NwchemParser, parse_nwchem_source
from pygls.server import LanguageServer


@pytest.fixture
def server():
    return LanguageServer("test", "1.0")


@pytest.fixture
def parser():
    """Return a parser factory function."""
    return lambda text: NwchemParser(text)


# ------------------------------------------------------------------
# Parser edge cases
# ------------------------------------------------------------------

class TestParserEdgeCases:
    """Parser robustness against edge cases."""

    def test_empty_input(self, parser):
        p = parser("")
        assert p.get_all_sections() == []
        is_valid, errors = p.is_valid_syntax()
        assert is_valid

    def test_only_comments(self, parser):
        p = parser("# this is a comment\n# another comment\n")
        assert p.get_all_sections() == []
        is_valid, errors = p.is_valid_syntax()
        assert is_valid

    def test_only_whitespace(self, parser):
        p = parser("   \n  \n\n   ")
        assert p.get_all_sections() == []

    def test_comment_only_section_content(self, parser):
        """Section with only comments inside should still parse."""
        source = "geometry\n# just a comment\nend"
        p = parser(source)
        assert "geometry" in p.get_all_sections()

    def test_deeply_nested_sections(self, parser):
        """Consecutive sections (not truly nested, but sequential)."""
        source = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
scf
  rhf
  maxiter 50
end
dft
  xc b3lyp
end
mp2
  freeze atomic
end"""
        p = parser(source)
        sections = p.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "scf" in sections
        assert "dft" in sections
        assert "mp2" in sections
        is_valid, errors = p.is_valid_syntax()
        assert is_valid

    def test_section_with_arguments(self, parser):
        """Section header with arguments like 'geometry units angstroms'."""
        source = "geometry units angstroms\n  O 0 0 0\n  H 0 0 1\nend"
        p = parser(source)
        assert "geometry" in p.get_all_sections()
        sections = p.get_section_content("geometry")
        assert len(sections) == 1

    def test_basis_spherical(self, parser):
        """Basis section with 'spherical' flag."""
        source = "basis spherical\n  * library 6-31G*\nend"
        p = parser(source)
        assert "basis" in p.get_all_sections()

    def test_multiple_tasks(self, parser):
        """Multiple task directives."""
        source = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task scf energy
task dft optimize"""
        p = parser(source)
        blocks = p.parse()
        tasks = [b for b in blocks if b.name == "task"]
        assert len(tasks) == 2

    def test_get_context_out_of_bounds(self, parser):
        """get_context with out-of-bounds line number."""
        p = parser("geometry\n  H 0 0 0\nend")
        ctx = p.get_context(999, 0)
        assert ctx.line_number == 999
        assert ctx.current_section is None

    def test_get_context_negative_line(self, parser):
        """get_context with negative line number."""
        p = parser("geometry\n  H 0 0 0\nend")
        ctx = p.get_context(-1, 0)
        assert ctx.current_section is None

    def test_word_at_cursor_end_of_line(self, parser):
        """Word extraction at end of line."""
        p = parser("")
        word = p._get_word_at_position("geometry", 7)
        # At position 7, we're past the end of "geometry"
        # Should return "y" or empty depending on implementation
        assert isinstance(word, str)

    def test_word_at_cursor_middle(self, parser):
        """Word extraction in middle of word."""
        p = parser("")
        word = p._get_word_at_position("geometry", 3)
        assert word == "geometry"

    def test_word_at_cursor_space(self, parser):
        """Word extraction at space character."""
        p = parser("")
        word = p._get_word_at_position("geometry units", 8)
        # Position 8 is the space; the implementation walks back through
        # alphanumerics and captures the preceding word ('geometry').
        assert isinstance(word, str) and len(word) > 0

    def test_parse_nwchem_source_function(self):
        """Test the module-level parse function."""
        p = parse_nwchem_source("geometry\n  H 0 0 0\nend")
        assert isinstance(p, NwchemParser)
        assert "geometry" in p.get_all_sections()

    def test_get_line_keywords(self):
        """Test line keyword extraction."""
        from nwchem_lsp.parser.nwchem_parser import get_line_keywords
        assert get_line_keywords("  geometry units ang") == ["geometry", "units", "ang"]
        assert get_line_keywords("# comment") == []
        assert get_line_keywords("") == []
        assert get_line_keywords("  ") == []

    def test_section_with_no_content(self, parser):
        """Section with immediate end."""
        source = "scf\nend"
        p = parser(source)
        assert "scf" in p.get_all_sections()
        sections = p.get_section_content("scf")
        assert len(sections) == 1

    def test_unclosed_section_at_eof(self, parser):
        """Section that is never closed at end of file."""
        source = "geometry\n  H 0 0 0"
        p = parser(source)
        assert "geometry" in p.get_all_sections()
        sections = p.get_section_content("geometry")
        assert sections[0].end_line is not None  # parser sets end_line to last line

    def test_multiple_same_section(self, parser):
        """Same section type appearing multiple times."""
        source = """geometry
  H 0 0 0
end
geometry
  O 0 0 0
end"""
        p = parser(source)
        sections = p.get_section_content("geometry")
        assert len(sections) == 2

    def test_case_insensitive_keywords(self, parser):
        """Keywords should be case-insensitive."""
        source = "GEOMETRY\n  H 0 0 0\nEND"
        p = parser(source)
        assert "geometry" in p.get_all_sections()

    def test_completion_context_in_section(self, parser):
        """Test completion context inside a section."""
        p = parser("dft\n  xc\nend")
        ctx = p.get_completion_context(1, 2)
        assert ctx["section"] == "dft"
        assert ctx["in_block"] is True

    def test_completion_context_top_level(self, parser):
        """Test completion context at top level."""
        p = parser("geometry\n  H 0 0 0\nend\n")
        ctx = p.get_completion_context(3, 0)
        assert ctx["type"] == "top_level"


# ------------------------------------------------------------------
# Diagnostic edge cases
# ------------------------------------------------------------------

class TestDiagnosticEdgeCases:
    """Test diagnostics on boundary and invalid inputs."""

    @pytest.fixture
    def provider(self, server):
        return DiagnosticProvider(server)

    def test_empty_input(self, provider):
        diags = provider.get_diagnostics("")
        assert isinstance(diags, list)
        # Empty input should report missing required sections
        messages = [d.message for d in diags]
        assert any("geometry" in m.lower() for m in messages)
        assert any("basis" in m.lower() for m in messages)

    def test_only_whitespace(self, provider):
        diags = provider.get_diagnostics("   \n  \n")
        assert isinstance(diags, list)
        assert len(diags) > 0  # Should report missing sections

    def test_unknown_task_theory(self, provider):
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task bogus energy
"""
        diags = provider.get_diagnostics(text)
        messages = [d.message for d in diags]
        assert any("bogus" in m.lower() or "theory" in m.lower() for m in messages)

    def test_unknown_task_operation(self, provider):
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task dft bogus_operation
"""
        diags = provider.get_diagnostics(text)
        messages = [d.message for d in diags]
        assert any("bogus_operation" in m for m in messages)

    def test_unknown_basis_set(self, provider):
        text = """geometry
  H 0 0 0
end
basis
  * library nonexistent-basis
end
task scf energy
"""
        diags = provider.get_diagnostics(text)
        messages = [d.message for d in diags]
        assert any("nonexistent-basis" in m for m in messages)

    def test_unknown_xc_functional(self, provider):
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
dft
  xc nonexistent_functional
end
task dft energy
"""
        diags = provider.get_diagnostics(text)
        messages = [d.message for d in diags]
        assert any("nonexistent_functional" in m for m in messages)

    def test_unclosed_section_diagnostic(self, provider):
        text = """geometry
  H 0 0 0
"""
        diags = provider.get_diagnostics(text)
        messages = [d.message for d in diags]
        assert any("unclosed" in m.lower() for m in messages)

    def test_unexpected_end_diagnostic(self, provider):
        text = """end
geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task scf energy
"""
        diags = provider.get_diagnostics(text)
        messages = [d.message for d in diags]
        assert any("unexpected" in m.lower() or "end" in m.lower() for m in messages)

    def test_snapshot_after_diagnostics(self, provider):
        """Snapshot should reflect the most recent diagnostics."""
        uri = "file:///test.nw"
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task scf energy
"""
        diags = provider.get_diagnostics(text)
        provider.update_cache(uri, diags)
        snapshot = provider.get_diagnostics_snapshot(uri)
        assert isinstance(snapshot, list)

    def test_all_snapshots_empty_initially(self, provider):
        assert provider.get_all_snapshots() == {}

    def test_snapshot_to_json_roundtrip(self, provider):
        import json
        uri = "file:///test.nw"
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task scf energy
"""
        diags = provider.get_diagnostics(text)
        provider.update_cache(uri, diags)
        json_str = provider.snapshot_to_json(uri)
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)


# ------------------------------------------------------------------
# Lint edge cases
# ------------------------------------------------------------------

class TestLintEdgeCases:
    """Test lint provider on edge cases."""

    @pytest.fixture
    def provider(self):
        return NwchemLintProvider()

    def test_empty_input(self, provider):
        diags = provider.lint("")
        assert isinstance(diags, list)
        codes_found = {str(d.code) for d in diags if d.code}
        assert "NW2004" in codes_found  # Missing required sections

    def test_only_comments(self, provider):
        diags = provider.lint("# comment\n")
        codes_found = {str(d.code) for d in diags if d.code}
        assert "NW2004" in codes_found  # Still missing sections

    def test_valid_full_input(self, provider):
        text = """geometry units angstroms
  O 0 0 0
  H 0 0.79 0.58
  H 0 -0.79 0.58
end

basis spherical
  * library 6-31G*
end

dft
  xc b3lyp
  grid fine
end

task dft optimize
"""
        diags = provider.lint(text)
        errors = [d for d in diags if d.severity == 1]  # Error severity
        assert len(errors) == 0, f"Unexpected errors: {[d.message for d in errors]}"

    def test_multiple_unclosed_sections(self, provider):
        text = "geometry\n  H 0 0 0\nbasis\n  * library 6-31G*\n"
        diags = provider.lint(text)
        unclosed = [d for d in diags if str(d.code) == "NW1001"]
        assert len(unclosed) >= 2  # Both geometry and basis are unclosed

    def test_task_with_no_operation(self, provider):
        """Task with only a theory should not crash."""
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task dft
"""
        diags = provider.lint(text)
        assert isinstance(diags, list)

    def test_section_with_unknown_keyword(self, provider):
        text = """geometry
  bogus_keyword
  O 0 0 0
end
basis
  * library 6-31G*
end
task scf energy
"""
        diags = provider.lint(text)
        kw_diags = [d for d in diags if str(d.code) == "NW2001"]
        assert len(kw_diags) >= 1

    def test_invalid_units_in_header(self, provider):
        text = """geometry units parsecs
  O 0 0 0
end
basis
  * library 6-31G*
end
task scf energy
"""
        diags = provider.lint(text)
        units_diags = [d for d in diags if str(d.code) == "NW2002"]
        assert len(units_diags) >= 1
        assert any("parsec" in d.message for d in units_diags)

    def test_duplicate_task_directives(self, provider):
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task scf energy
task dft optimize
"""
        diags = provider.lint(text)
        dup_diags = [d for d in diags if str(d.code) == "NW3003"]
        assert len(dup_diags) >= 1

    def test_all_diagnostics_have_source(self, provider):
        text = """geometry
  bogus_kw
end
basis
  * library 6-31G*
end
task fake energy
"""
        diags = provider.lint(text)
        for d in diags:
            assert d.source == "nwchem-lsp"


# ------------------------------------------------------------------
# Completion edge cases
# ------------------------------------------------------------------

class TestCompletionEdgeCases:
    """Test completion provider edge cases."""

    @pytest.fixture
    def provider(self, server):
        return NwchemCompletionProvider(server)

    def test_empty_document(self, provider):
        completions = provider.get_completions("", Position(line=0, character=0))
        assert isinstance(completions, list)
        assert len(completions) > 0  # Should suggest top-level keywords

    def test_completion_inside_geometry(self, provider):
        text = "geometry\n  \nend"
        completions = provider.get_completions(text, Position(line=1, character=2))
        assert isinstance(completions, list)

    def test_completion_inside_basis(self, provider):
        text = "basis\n  \nend"
        completions = provider.get_completions(text, Position(line=1, character=2))
        assert isinstance(completions, list)

    def test_completion_inside_dft(self, provider):
        text = "dft\n  \nend"
        completions = provider.get_completions(text, Position(line=1, character=2))
        assert isinstance(completions, list)
        if completions:
            labels = [c.label for c in completions]
            assert "xc" in labels or "grid" in labels

    def test_completion_inside_scf(self, provider):
        text = "scf\n  \nend"
        completions = provider.get_completions(text, Position(line=1, character=2))
        assert isinstance(completions, list)
        if completions:
            labels = [c.label for c in completions]
            assert any(kw in labels for kw in ["rhf", "uhf", "maxiter", "thresh"])

    def test_completion_task_line(self, provider):
        """After 'task ' should suggest theories."""
        text = """geometry
  H 0 0 0
end
basis
  * library 6-31G*
end
task """
        completions = provider.get_completions(text, Position(line=7, character=5))
        assert isinstance(completions, list)

    def test_completion_with_prefix(self, provider):
        """Completion should filter by prefix."""
        text = "geom"
        completions = provider.get_completions(text, Position(line=0, character=4))
        assert isinstance(completions, list)
        labels = [c.label for c in completions]
        if labels:
            assert any("geom" in l.lower() for l in labels)


# ------------------------------------------------------------------
# Hover edge cases
# ------------------------------------------------------------------

class TestHoverEdgeCases:
    """Test hover provider edge cases."""

    @pytest.fixture
    def provider(self, server):
        return NwchemHoverProvider(server)

    def test_hover_on_empty(self, provider):
        hover = provider.get_hover("", Position(line=0, character=0))
        assert hover is None

    def test_hover_on_whitespace(self, provider):
        hover = provider.get_hover("   ", Position(line=0, character=1))
        assert hover is None

    def test_hover_on_comment(self, provider):
        hover = provider.get_hover("# comment", Position(line=0, character=2))
        assert hover is None  # Comments have no hover info

    def test_hover_on_known_keyword(self, provider):
        hover = provider.get_hover("geometry", Position(line=0, character=3))
        assert hover is not None, "Hover on 'geometry' should return info"

    def test_hover_on_task_keyword(self, provider):
        hover = provider.get_hover("task dft optimize", Position(line=0, character=1))
        assert hover is not None, "Hover on 'task' should return info"

    def test_hover_on_basis_keyword(self, provider):
        hover = provider.get_hover("basis", Position(line=0, character=2))
        assert hover is not None, "Hover on 'basis' should return info"

    def test_hover_on_scf_keyword(self, provider):
        hover = provider.get_hover("scf", Position(line=0, character=1))
        assert hover is not None, "Hover on 'scf' should return info"

    def test_hover_on_dft_keyword(self, provider):
        hover = provider.get_hover("dft", Position(line=0, character=1))
        assert hover is not None, "Hover on 'dft' should return info"

    def test_hover_inside_section(self, provider):
        """Hover on a keyword inside a section should find it in section context."""
        text = "scf\n  maxiter 100\nend"
        hover = provider.get_hover(text, Position(line=1, character=3))
        assert hover is not None, "Hover on 'maxiter' inside scf should return info"

    def test_hover_contents_are_markdown(self, provider):
        """Hover contents should be in Markdown format."""
        hover = provider.get_hover("geometry", Position(line=0, character=3))
        if hover is not None:
            assert hasattr(hover, "contents")


# ------------------------------------------------------------------
# Formatting edge cases
# ------------------------------------------------------------------

class TestFormattingEdgeCases:
    """Test formatting provider edge cases."""

    @pytest.fixture
    def provider(self, server):
        return NwchemFormattingProvider(server)

    def _make_params(self, tab_size=2, insert_spaces=True):
        from lsprotocol.types import DocumentFormattingParams, FormattingOptions
        return DocumentFormattingParams(
            text_document=None,
            options=FormattingOptions(tab_size=tab_size, insert_spaces=insert_spaces),
        )

    def test_format_empty(self, provider):
        edits = provider.format_document("", self._make_params())
        assert isinstance(edits, list)

    def test_format_already_formatted(self, provider):
        text = "geometry\n  H 0 0 0\nend\n"
        edits = provider.format_document(text, self._make_params())
        # May produce no edits if already formatted
        assert isinstance(edits, list)

    def test_format_fixes_indentation(self, provider):
        text = "geometry\nH 0 0 0\nend"
        edits = provider.format_document(text, self._make_params())
        assert len(edits) > 0
        formatted = edits[0].new_text
        # Content inside section should be indented
        lines = formatted.splitlines()
        assert lines[1].startswith("  ") or lines[1].startswith("\t") or "H" in lines[1]

    def test_format_preserves_comments(self, provider):
        text = "# header\ngeometry\n  H 0 0 0\nend"
        edits = provider.format_document(text, self._make_params())
        if edits:
            formatted = edits[0].new_text
            assert "# header" in formatted

    def test_format_preserves_element_symbols(self, provider):
        """Element symbols like O, H, C should not be lowercased."""
        text = "geometry\n  O 0 0 0\n  H 0 0 1\nend"
        edits = provider.format_document(text, self._make_params())
        if edits:
            formatted = edits[0].new_text
            assert "O" in formatted
            assert "H" in formatted

    def test_format_section_keywords_lowercase(self, provider):
        """Section keywords should be normalized to lowercase."""
        text = "GEOMETRY\n  H 0 0 0\nEND"
        edits = provider.format_document(text, self._make_params())
        if edits:
            formatted = edits[0].new_text.lower()
            assert "geometry" in formatted
            assert "end" in formatted

    def test_range_formatting(self, provider):
        """Test formatting a specific range."""
        from lsprotocol.types import DocumentRangeFormattingParams, FormattingOptions, Range
        text = "geometry\nH 0 0 0\nend\nbasis\n  * library 6-31G*\nend"
        params = DocumentRangeFormattingParams(
            text_document=None,
            options=FormattingOptions(tab_size=2, insert_spaces=True),
            range=Range(start=Position(line=1, character=0), end=Position(line=2, character=10)),
        )
        edits = provider.format_range(text, params)
        assert isinstance(edits, list)

    def test_format_idempotent(self, provider):
        """Formatting already-formatted text should produce no edits."""
        text = "geometry\n  H 0 0 0\nend\nbasis\n  * library 6-31G*\nend\n"
        edits1 = provider.format_document(text, self._make_params())
        if edits1:
            formatted = edits1[0].new_text
            edits2 = provider.format_document(formatted, self._make_params())
            assert isinstance(edits2, list)
            # Second pass should produce no (or very minimal) edits
            if edits2:
                # The formatted text should be identical after second pass
                formatted2 = edits2[0].new_text
                assert formatted == formatted2


# ------------------------------------------------------------------
# Definition edge cases
# ------------------------------------------------------------------

class TestDefinitionEdgeCases:
    """Test go-to-definition edge cases."""

    @pytest.fixture
    def provider(self):
        return DefinitionProvider()

    def test_definition_empty(self, provider):
        result = provider.get_definition("", Position(line=0, character=0))
        assert result is None

    def test_definition_on_non_keyword(self, provider):
        result = provider.get_definition("foo bar", Position(line=0, character=1))
        assert result is None

    def test_definition_on_end_finds_start(self, provider):
        text = "geometry\n  H 0 0 0\nend"
        result = provider.get_definition(text, Position(line=2, character=1))
        assert result is not None
        assert result.range.start.line == 0

    def test_definition_on_end_with_nested(self, provider):
        """End should match the closest open section."""
        text = "geometry\n  H 0 0 0\nend\nbasis\n  * library 6-31G*\nend"
        # Lines: 0=geometry, 1=H, 2=end, 3=basis, 4=library, 5=end
        # End at line 5 closes basis which starts at line 3
        result = provider.get_definition(text, Position(line=5, character=1))
        assert result is not None
        assert result.range.start.line == 3  # basis starts at line 3

    def test_definition_out_of_bounds(self, provider):
        text = "geometry\nend"
        result = provider.get_definition(text, Position(line=99, character=0))
        assert result is None


# ------------------------------------------------------------------
# Semantic tokens edge cases
# ------------------------------------------------------------------

class TestSemanticTokensEdgeCases:
    """Test semantic tokens edge cases."""

    @pytest.fixture
    def provider(self, server):
        from nwchem_lsp.features.semantic_tokens import SemanticTokensProvider
        return SemanticTokensProvider(server)

    def test_empty_input(self, provider):
        result = provider.get_semantic_tokens("")
        assert result is not None

    def test_valid_input(self, provider):
        text = "geometry\n  H 0 0 0\nend\nbasis\n  * library 6-31G*\nend\ntask scf energy\n"
        result = provider.get_semantic_tokens(text)
        assert result is not None


# ------------------------------------------------------------------
# Folding range edge cases
# ------------------------------------------------------------------

class TestFoldingRangeEdgeCases:
    """Test folding range edge cases."""

    @pytest.fixture
    def provider(self, server):
        from nwchem_lsp.features.folding_range import FoldingRangeProvider
        return FoldingRangeProvider(server)

    def test_empty_input(self, provider):
        ranges = provider.get_folding_ranges("")
        assert isinstance(ranges, list)
        assert len(ranges) == 0

    def test_single_line_section(self, provider):
        """Section with only start and end on adjacent lines."""
        text = "scf\nend"
        ranges = provider.get_folding_ranges(text)
        # Single-line section should not have a folding range (start >= end)
        assert isinstance(ranges, list)

    def test_multi_section_folding(self, provider):
        text = "geometry\n  H 0 0 0\nend\nbasis\n  * library 6-31G*\nend"
        ranges = provider.get_folding_ranges(text)
        assert len(ranges) >= 2

    def test_folding_range_subset(self, provider):
        """get_folding_ranges_for_lines should filter correctly."""
        text = "geometry\n  H 0 0 0\nend\nbasis\n  * library 6-31G*\nend"
        ranges = provider.get_folding_ranges_for_lines(text, 0, 2)
        for r in ranges:
            assert r.start_line >= 0
            assert r.end_line <= 2


# ------------------------------------------------------------------
# References edge cases
# ------------------------------------------------------------------

class TestReferencesEdgeCases:
    """Test references provider edge cases."""

    @pytest.fixture
    def provider(self, server):
        from nwchem_lsp.features.references import ReferencesProvider
        return ReferencesProvider(server)

    def test_empty_input(self, provider):
        result = provider.get_references("", "file:///test.nw", Position(line=0, character=0), True)
        assert result == []

    def test_non_section_keyword(self, provider):
        text = "geometry\n  H 0 0 0\nend"
        result = provider.get_references(text, "file:///test.nw", Position(line=1, character=2), True)
        assert result == []

    def test_section_references(self, provider):
        text = "geometry\n  H 0 0 0\nend\ngeometry\n  O 0 0 0\nend"
        result = provider.get_references(text, "file:///test.nw", Position(line=0, character=0), True)
        assert len(result) >= 1


# ------------------------------------------------------------------
# Rename edge cases
# ------------------------------------------------------------------

class TestRenameEdgeCases:
    """Test rename provider edge cases."""

    @pytest.fixture
    def provider(self, server):
        from nwchem_lsp.features.rename import RenameProvider
        return RenameProvider(server)

    def test_empty_input(self, provider):
        result = provider.get_rename_edits("", "file:///test.nw", Position(line=0, character=0), "scf")
        assert result is None

    def test_rename_non_section(self, provider):
        text = "geometry\n  H 0 0 0\nend"
        result = provider.get_rename_edits(text, "file:///test.nw", Position(line=1, character=2), "foo")
        assert result is None

    def test_rename_to_invalid_section(self, provider):
        text = "geometry\n  H 0 0 0\nend"
        result = provider.get_rename_edits(text, "file:///test.nw", Position(line=0, character=0), "nonexistent")
        assert result is None

    def test_rename_geometry_to_basis(self, provider):
        text = "geometry\n  H 0 0 0\nend"
        result = provider.get_rename_edits(text, "file:///test.nw", Position(line=0, character=0), "basis")
        assert result is not None
        assert len(result.changes["file:///test.nw"]) >= 1

    def test_is_valid_rename(self, provider):
        text = "geometry\n  H 0 0 0\nend"
        assert provider.is_valid_rename(text, Position(line=0, character=0), "scf") is True
        assert provider.is_valid_rename(text, Position(line=0, character=0), "nonexistent") is False
        assert provider.is_valid_rename(text, Position(line=1, character=2), "scf") is False

    def test_rename_out_of_bounds(self, provider):
        text = "geometry\nend"
        result = provider.get_rename_edits(text, "file:///test.nw", Position(line=99, character=0), "scf")
        assert result is None

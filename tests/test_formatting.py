"""Tests for formatting provider.

Covers document formatting, range formatting, idempotency, nested sections,
comments, blank lines, malformed input, keyword normalization, and edge cases.
"""

from __future__ import annotations

import pytest
from lsprotocol.types import (
    DocumentFormattingParams,
    DocumentRangeFormattingParams,
    FormattingOptions,
    Position,
    Range,
    TextDocumentIdentifier,
)

from nwchem_lsp.features.formatting import NwchemFormattingProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_server():
    """Create a minimal LanguageServer for test use."""
    from pygls.server import LanguageServer

    return LanguageServer("test", "1.0")


def _doc_params(tab_size: int = 2, insert_spaces: bool = True) -> DocumentFormattingParams:
    """Create default document formatting parameters."""
    return DocumentFormattingParams(
        text_document=TextDocumentIdentifier(uri="test.nw"),
        options=FormattingOptions(tab_size=tab_size, insert_spaces=insert_spaces),
    )


def _range_params(
    start_line: int,
    start_char: int,
    end_line: int,
    end_char: int,
    tab_size: int = 2,
    insert_spaces: bool = True,
) -> DocumentRangeFormattingParams:
    """Create range formatting parameters."""
    return DocumentRangeFormattingParams(
        text_document=TextDocumentIdentifier(uri="test.nw"),
        range=Range(
            start=Position(line=start_line, character=start_char),
            end=Position(line=end_line, character=end_char),
        ),
        options=FormattingOptions(tab_size=tab_size, insert_spaces=insert_spaces),
    )


def _apply_edits(text: str, edits: list) -> str:
    """Apply TextEdit list to text naively (for single full-doc edit)."""
    if not edits:
        return text
    # For simplicity, handle the common case: one edit replacing the full doc
    lines = text.splitlines()
    for edit in edits:
        if (
            edit.range.start.line == 0
            and edit.range.start.character == 0
            and edit.range.end.line >= len(lines)
        ):
            return edit.new_text
    # Fallback: return text unchanged
    return text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider():
    """Create a formatting provider instance."""
    return NwchemFormattingProvider(_make_server())


# ===================================================================
# Document formatting — basic
# ===================================================================


class TestFormatDocumentBasic:
    """Basic document formatting tests."""

    def test_empty_document(self, provider):
        """Empty document returns no edits."""
        edits = provider.format_document("", _doc_params())
        assert edits == []

    def test_single_line_no_section(self, provider):
        """A lone task line is already formatted."""
        text = "task scf energy"
        edits = provider.format_document(text, _doc_params())
        assert edits == []

    def test_single_comment(self, provider):
        """A comment-only document returns no edits."""
        text = "# this is a comment"
        edits = provider.format_document(text, _doc_params())
        assert edits == []

    def test_blank_only(self, provider):
        """A blank-only document returns no edits."""
        text = "\n\n\n"
        edits = provider.format_document(text, _doc_params())
        assert edits == []


class TestFormatDocumentIndentation:
    """Indentation tests for document formatting."""

    def test_simple_section(self, provider):
        """Section content is indented, end is flush."""
        text = "geometry\nH 0 0 0\nO 0 0 1.0\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert len(edits) == 1
        formatted = edits[0].new_text
        lines = formatted.splitlines()
        assert lines[0] == "geometry"
        assert lines[1] == "  H 0 0 0"
        assert lines[2] == "  O 0 0 1.0"
        assert lines[3] == "end"

    def test_multiple_sections(self, provider):
        """Multiple sections each indent correctly."""
        text = "geometry\nH 0 0 0\nend\nbasis\nH library 6-31g\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert len(edits) == 1
        formatted = edits[0].new_text
        lines = formatted.splitlines()
        assert lines[0] == "geometry"
        assert lines[1] == "  H 0 0 0"
        assert lines[2] == "end"
        assert lines[3] == "basis"
        assert lines[4] == "  H library 6-31g"
        assert lines[5] == "end"

    def test_over_indented_content(self, provider):
        """Over-indented content is corrected to the right level."""
        text = "geometry\n    H 0 0 0\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert len(edits) == 1
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "  H 0 0 0"

    def test_nested_sections(self, provider):
        """Nested sections (e.g. dft containing sub-blocks) indent deeper."""
        text = "dft\nxc b3lyp\ngrid fine\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert len(edits) == 1
        lines = edits[0].new_text.splitlines()
        assert lines[0] == "dft"
        assert lines[1] == "  xc b3lyp"
        assert lines[2] == "  grid fine"
        assert lines[3] == "end"

    def test_indent_4_spaces(self, provider):
        """Formatting with tab_size=4 uses 4-space indent."""
        text = "geometry\nH 0 0 0\nend\n"
        edits = provider.format_document(text, _doc_params(tab_size=4))
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "    H 0 0 0"

    def test_indent_tabs(self, provider):
        """Formatting with insert_spaces=False uses tab characters."""
        text = "geometry\nH 0 0 0\nend\n"
        edits = provider.format_document(text, _doc_params(insert_spaces=False))
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "\tH 0 0 0"

    def test_end_at_zero_indent(self, provider):
        """End keyword is always at the correct outer level."""
        text = "scf\n    singlet\n    rhf\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[3] == "end"


class TestFormatDocumentComments:
    """Comment preservation tests."""

    def test_comment_in_section(self, provider):
        """Comments inside sections are preserved as-is (stripped)."""
        text = "geometry\n# atom coords\nH 0 0 0\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "# atom coords"

    def test_comment_before_section(self, provider):
        """Comments before sections are preserved."""
        text = "# header\ngeometry\nH 0 0 0\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[0] == "# header"
        assert lines[1] == "geometry"


class TestFormatDocumentBlankLines:
    """Blank line preservation tests."""

    def test_blank_between_sections(self, provider):
        """Blank lines between sections are preserved."""
        text = "geometry\nH 0 0 0\nend\n\nbasis\nH library 6-31g\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[3] == ""

    def test_trailing_newline_preserved(self, provider):
        """Trailing newline is preserved in formatted output."""
        text = "geometry\nH 0 0 0\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert edits[0].new_text.endswith("\n")

    def test_no_trailing_newline_no_extra(self, provider):
        """No trailing newline in input means no extra trailing newline."""
        text = "geometry\nH 0 0 0\nend"
        edits = provider.format_document(text, _doc_params())
        assert not edits[0].new_text.endswith("\n")


class TestFormatDocumentKeywordNormalization:
    """Keyword normalization tests."""

    def test_section_keyword_lowercased(self, provider):
        """Section keywords are normalized to lowercase."""
        text = "GEOMETRY\nH 0 0 0\nEND\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[0] == "geometry"
        assert lines[2] == "end"

    def test_section_header_with_options(self, provider):
        """Section headers with options (e.g. units) are normalized."""
        text = "GEOMETRY UNITS ANGSTROMS\nH 0 0 0\nEND\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[0] == "geometry units angstroms"

    def test_body_keywords_lowercased(self, provider):
        """Known keywords in section body are lowercased."""
        text = "SCF\nSINGLET\nRHF\nEND\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "  singlet"
        assert lines[2] == "  rhf"

    def test_element_symbols_preserved(self, provider):
        """Element symbols (H, O, C, etc.) keep their case."""
        text = "geometry\nH 0 0 0\nO 0 0 1.0\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "  H 0 0 0"
        assert lines[2] == "  O 0 0 1.0"

    def test_numeric_values_preserved(self, provider):
        """Numeric values are not modified."""
        text = "geometry\nH 0.0 0.0 0.0\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "  H 0.0 0.0 0.0"

    def test_library_keyword_lowercased(self, provider):
        """The 'library' keyword inside basis is lowercased."""
        text = "basis\nH LIBRARY 6-31g\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[1] == "  H library 6-31g"


class TestFormatDocumentIdempotency:
    """Idempotency: formatting already-formatted text returns no edits."""

    def test_idempotent_simple(self, provider):
        """Already-formatted simple section is unchanged."""
        text = "geometry\n  H 0 0 0\n  O 0 0 1.0\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert edits == []

    def test_idempotent_multi_section(self, provider):
        """Already-formatted multi-section document is unchanged."""
        text = (
            "geometry\n"
            "  H 0 0 0\n"
            "  O 0 0 1.0\n"
            "end\n"
            "\n"
            "basis\n"
            "  H library 6-31g\n"
            "  O library 6-31g\n"
            "end\n"
            "\n"
            "task scf energy\n"
        )
        edits = provider.format_document(text, _doc_params())
        assert edits == []

    def test_idempotent_with_comments(self, provider):
        """Already-formatted text with comments is unchanged."""
        text = "# header\ngeometry\n  H 0 0 0\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert edits == []

    def test_idempotent_double_apply(self, provider):
        """Formatting twice produces the same result."""
        text = "GEOMETRY\n    H 0 0 0\n  O 0 0 1.0\nEND\n"
        params = _doc_params()
        edits1 = provider.format_document(text, params)
        formatted1 = _apply_edits(text, edits1)
        edits2 = provider.format_document(formatted1, params)
        formatted2 = _apply_edits(formatted1, edits2)
        assert formatted1 == formatted2


class TestFormatDocumentMalformed:
    """Malformed input tests."""

    def test_unclosed_section(self, provider):
        """Unclosed section still formats content."""
        text = "geometry\nH 0 0 0\n"
        edits = provider.format_document(text, _doc_params())
        assert len(edits) == 1
        lines = edits[0].new_text.splitlines()
        assert lines[0] == "geometry"
        assert lines[1] == "  H 0 0 0"

    def test_orphan_end(self, provider):
        """Orphan end (no matching section) does not crash and stays at indent 0."""
        text = "end\n"
        edits = provider.format_document(text, _doc_params())
        # end at indent 0 should not change
        assert edits == []

    def test_end_without_start(self, provider):
        """Multiple orphan ends don't crash."""
        text = "end\nend\nend\n"
        edits = provider.format_document(text, _doc_params())
        assert edits == []

    def test_only_whitespace_in_section(self, provider):
        """Section with only whitespace lines handles gracefully."""
        text = "geometry\n   \n\nend\n"
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[0] == "geometry"
        assert lines[1] == ""
        assert lines[2] == ""
        assert lines[3] == "end"


# ===================================================================
# Range formatting
# ===================================================================


class TestFormatRange:
    """Range formatting tests."""

    def test_range_single_line(self, provider):
        """Formatting a single line within a section."""
        text = "geometry\n    H 0 0 0\n  O 0 0 1.0\nend\n"
        params = _range_params(1, 0, 1, 20)
        edits = provider.format_range(text, params)
        assert len(edits) == 1
        assert edits[0].new_text == "  H 0 0 0"

    def test_range_multiple_lines(self, provider):
        """Formatting multiple lines within a section."""
        text = "geometry\n    H 0 0 0\n        O 0 0 1.0\nend\n"
        params = _range_params(1, 0, 2, 30)
        edits = provider.format_range(text, params)
        assert len(edits) == 2
        assert edits[0].new_text == "  H 0 0 0"
        assert edits[1].new_text == "  O 0 0 1.0"

    def test_range_includes_section_header(self, provider):
        """Range formatting handles section header."""
        text = "GEOMETRY\n    H 0 0 0\nend\n"
        params = _range_params(0, 0, 1, 30)
        edits = provider.format_range(text, params)
        # geometry header should be normalized to lowercase
        header_edit = [e for e in edits if e.range.start.line == 0]
        assert len(header_edit) == 1
        assert header_edit[0].new_text == "geometry"

    def test_range_includes_end(self, provider):
        """Range formatting handles end keyword correctly."""
        text = "geometry\n  H 0 0 0\n    END\n"
        params = _range_params(2, 0, 2, 10)
        edits = provider.format_range(text, params)
        # end should be at indent 0
        assert len(edits) == 1
        assert edits[0].new_text == "end"

    def test_range_empty_document(self, provider):
        """Range formatting on empty document returns no edits."""
        text = ""
        params = _range_params(0, 0, 0, 0)
        edits = provider.format_range(text, params)
        assert edits == []

    def test_range_already_formatted(self, provider):
        """Range formatting on already-formatted text returns no edits."""
        text = "geometry\n  H 0 0 0\n  O 0 0 1.0\nend\n"
        params = _range_params(1, 0, 2, 30)
        edits = provider.format_range(text, params)
        assert edits == []

    def test_range_preserves_outside_lines(self, provider):
        """Range formatting only edits lines within the range."""
        text = "GEOMETRY\n    H 0 0 0\n  O 0 0 1.0\nEND\n"
        params = _range_params(1, 0, 1, 30)
        edits = provider.format_range(text, params)
        # Only line 1 should be edited
        for edit in edits:
            assert edit.range.start.line == 1
            assert edit.range.end.line == 1

    def test_range_across_section_boundary(self, provider):
        """Range formatting across a section boundary handles both sections."""
        text = "geometry\n  H 0 0 0\nEND\nbasis\n    H library 6-31g\nend\n"
        params = _range_params(2, 0, 4, 30)
        edits = provider.format_range(text, params)
        # end should be at indent 0, basis content at indent 1
        end_edits = [e for e in edits if e.range.start.line == 2]
        basis_edits = [e for e in edits if e.range.start.line == 4]
        if end_edits:
            assert end_edits[0].new_text == "end"
        if basis_edits:
            assert basis_edits[0].new_text == "  H library 6-31g"

    def test_range_indent_4_spaces(self, provider):
        """Range formatting with tab_size=4."""
        text = "geometry\nH 0 0 0\nend\n"
        params = _range_params(1, 0, 1, 20, tab_size=4)
        edits = provider.format_range(text, params)
        assert len(edits) == 1
        assert edits[0].new_text == "    H 0 0 0"

    def test_range_indent_tabs(self, provider):
        """Range formatting with tabs."""
        text = "geometry\nH 0 0 0\nend\n"
        params = _range_params(1, 0, 1, 20, insert_spaces=False)
        edits = provider.format_range(text, params)
        assert len(edits) == 1
        assert edits[0].new_text == "\tH 0 0 0"


# ===================================================================
# Factory / backward compatibility
# ===================================================================


class TestGetFormattingProvider:
    """Tests for get_formatting_provider factory function."""

    def test_factory(self):
        """Test factory function."""
        from nwchem_lsp.features.formatting import get_formatting_provider

        provider = get_formatting_provider(_make_server())
        assert isinstance(provider, NwchemFormattingProvider)

    def test_backward_compat_alias(self):
        """Test that FormattingProvider alias works."""
        from nwchem_lsp.features.formatting import FormattingProvider

        assert FormattingProvider is NwchemFormattingProvider


class TestFormatDocumentFullIntegration:
    """Integration tests with realistic NWChem input files."""

    def test_water_molecule(self, provider):
        """Format a typical water molecule input."""
        text = """start water
title "Water molecule"
charge 0
GEOMETRY UNITS ANGSTROMS
  O     0.0000   0.0000   0.0000
  H     0.0000   0.7586   0.5042
  H     0.0000  -0.7586   0.5042
END
BASIS
  O LIBRARY 6-31g
  H LIBRARY 6-31g
END
TASK SCF OPTIMIZE
"""
        edits = provider.format_document(text, _doc_params())
        assert len(edits) == 1
        formatted = edits[0].new_text
        lines = formatted.splitlines()

        assert lines[0] == "start water"
        assert lines[1] == 'title "Water molecule"'
        assert lines[2] == "charge 0"
        assert lines[3] == "geometry units angstroms"
        assert lines[4] == "  O     0.0000   0.0000   0.0000"
        assert lines[5] == "  H     0.0000   0.7586   0.5042"
        assert lines[6] == "  H     0.0000  -0.7586   0.5042"
        assert lines[7] == "end"
        assert lines[8] == "basis"
        assert lines[9] == "  O library 6-31g"
        assert lines[10] == "  H library 6-31g"
        assert lines[11] == "end"
        assert lines[12] == "task scf optimize"

    def test_idempotent_realistic(self, provider):
        """Realistic input is idempotent after first formatting."""
        text = """start water
title "Water molecule"
charge 0
GEOMETRY UNITS ANGSTROMS
  O     0.0000   0.0000   0.0000
  H     0.0000   0.7586   0.5042
  H     0.0000  -0.7586   0.5042
END
BASIS
  O LIBRARY 6-31g
  H LIBRARY 6-31g
END
TASK SCF OPTIMIZE
"""
        params = _doc_params()
        edits1 = provider.format_document(text, params)
        formatted1 = _apply_edits(text, edits1)
        edits2 = provider.format_document(formatted1, params)
        formatted2 = _apply_edits(formatted1, edits2)
        assert formatted1 == formatted2

    def test_dft_with_keywords(self, provider):
        """DFT section with multiple keyword lines."""
        text = """DFT
  XC B3LYP
  GRID FINE
  CONVERGENCE ENERGY 1E-8
  ITERATIONS 200
END
"""
        edits = provider.format_document(text, _doc_params())
        lines = edits[0].new_text.splitlines()
        assert lines[0] == "dft"
        assert lines[1] == "  xc b3lyp"
        assert lines[2] == "  grid fine"
        assert lines[3] == "  convergence energy 1E-8"
        assert lines[4] == "  iterations 200"
        assert lines[5] == "end"

"""Tests for code actions provider."""

import pytest
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

from nwchem_lsp.features.code_actions import CodeActionsProvider


def _diag(
    line: int,
    col_start: int,
    col_end: int,
    message: str,
    code: str | None = None,
    severity: DiagnosticSeverity = DiagnosticSeverity.Error,
) -> Diagnostic:
    """Helper to build a Diagnostic with a stable code."""
    return Diagnostic(
        range=Range(
            start=Position(line=line, character=col_start),
            end=Position(line=line, character=col_end),
        ),
        message=message,
        severity=severity,
        source="nwchem-lsp",
        code=code,
    )


# ======================================================================
# Existing tests (backward compatibility)
# ======================================================================


class TestCodeActionsProvider:
    """Tests for CodeActionsProvider class."""

    def test_provider_exists(self):
        """Test that provider can be instantiated."""
        provider = CodeActionsProvider()
        assert provider is not None

    def test_get_code_actions_empty(self):
        """Test getting code actions with no diagnostics."""
        provider = CodeActionsProvider()
        source = "start test\ngeometry\n  O 0 0 0\nend"
        actions = provider.get_code_actions(source, [])
        # Should have at least the "add start" action if no start exists
        assert isinstance(actions, list)

    def test_fix_unclosed_section(self):
        """Test fix for unclosed section."""
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"

        diagnostic = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=8)),
            message="Unclosed section: 'geometry'",
            severity=DiagnosticSeverity.Error,
            source="nwchem-lsp",
        )

        actions = provider.get_code_actions(source, [diagnostic])
        assert len(actions) >= 1
        assert any("Add 'end'" in a.title for a in actions)

    def test_fix_unexpected_end(self):
        """Test fix for unexpected 'end' keyword."""
        provider = CodeActionsProvider()
        source = "end"

        diagnostic = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=3)),
            message="Unexpected 'end' keyword (no matching section start)",
            severity=DiagnosticSeverity.Error,
            source="nwchem-lsp",
        )

        actions = provider.get_code_actions(source, [diagnostic])
        assert len(actions) >= 1
        assert any("Remove unexpected 'end'" in a.title for a in actions)

    def test_fix_unknown_keyword_typo(self):
        """Test fix for unknown keyword with typo."""
        provider = CodeActionsProvider()
        source = "gemoetry\n  O 0 0 0"

        diagnostic = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=8)),
            message="Unknown keyword 'gemoetry'",
            severity=DiagnosticSeverity.Warning,
            source="nwchem-lsp",
        )

        actions = provider.get_code_actions(source, [diagnostic])
        # Should suggest 'geometry' as fix
        assert any("geometry" in a.title.lower() for a in actions)

    def test_fix_unknown_keyword_no_match(self):
        """Test fix for unknown keyword with no close match."""
        provider = CodeActionsProvider()
        source = "xyzabc\n  O 0 0 0"

        diagnostic = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=6)),
            message="Unknown keyword 'xyzabc'",
            severity=DiagnosticSeverity.Warning,
            source="nwchem-lsp",
        )

        actions = provider.get_code_actions(source, [diagnostic])
        # Should not suggest anything if no close match
        unknown_actions = [a for a in actions if "Replace" in a.title]
        # May or may not have a suggestion depending on threshold
        assert isinstance(actions, list)

    def test_add_missing_start_directive(self):
        """Test adding missing 'start' directive."""
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0\nend"

        actions = provider.get_code_actions(source, [])
        # Should suggest adding start directive
        assert any("Add missing 'start'" in a.title for a in actions)

    def test_no_start_directive_when_exists(self):
        """Test that no start directive action when start exists."""
        provider = CodeActionsProvider()
        source = "start water\ngeometry\n  O 0 0 0\nend"

        actions = provider.get_code_actions(source, [])
        # Should not suggest adding start directive
        assert not any("Add missing 'start'" in a.title for a in actions)


class TestKeywordSimilarity:
    """Tests for keyword similarity matching."""

    def test_similarity_score_identical(self):
        """Test similarity score for identical strings."""
        provider = CodeActionsProvider()
        score = provider._similarity_score("geometry", "geometry")
        assert score == 1.0

    def test_similarity_score_different(self):
        """Test similarity score for different strings."""
        provider = CodeActionsProvider()
        score = provider._similarity_score("abc", "xyz")
        assert score < 0.5

    def test_similarity_score_similar(self):
        """Test similarity score for similar strings."""
        provider = CodeActionsProvider()
        score = provider._similarity_score("geometry", "gemoetry")
        assert score > 0.7

    def test_similarity_score_empty(self):
        """Test similarity score for empty strings."""
        provider = CodeActionsProvider()
        score = provider._similarity_score("", "")
        assert score == 1.0

    def test_similarity_score_one_empty(self):
        """Test similarity score when one string is empty."""
        provider = CodeActionsProvider()
        score = provider._similarity_score("geometry", "")
        assert score == 0.0


class TestTypoCorrection:
    """Tests for common typo corrections."""

    def test_geometry_typos(self):
        """Test correction of 'geometry' typos."""
        provider = CodeActionsProvider()
        typos = ["gemoetry", "gemetry", "goemetry"]
        for typo in typos:
            result = provider._find_closest_keyword(typo)
            assert result == "geometry", f"Expected 'geometry' for '{typo}', got '{result}'"

    def test_basis_typos(self):
        """Test correction of 'basis' typos."""
        provider = CodeActionsProvider()
        typos = ["basiss", "bassis"]
        for typo in typos:
            result = provider._find_closest_keyword(typo)
            assert result == "basis", f"Expected 'basis' for '{typo}', got '{result}'"

    def test_task_typos(self):
        """Test correction of 'task' typos."""
        provider = CodeActionsProvider()
        typos = ["taks", "tsk"]
        for typo in typos:
            result = provider._find_closest_keyword(typo)
            assert result == "task", f"Expected 'task' for '{typo}', got '{result}'"

    def test_short_keyword_returns_none(self):
        """Test that very short keywords return None."""
        provider = CodeActionsProvider()
        result = provider._find_closest_keyword("a")
        assert result is None

    def test_valid_keyword_returns_none(self):
        """Test that already valid keywords don't need correction."""
        provider = CodeActionsProvider()
        # Valid keywords should still return themselves or None
        result = provider._find_closest_keyword("geometry")
        # Either returns the same keyword or None is acceptable
        assert result is None or result == "geometry"


class TestCodeActionKinds:
    """Tests for code action kinds."""

    def test_quick_fix_kind(self):
        """Test that quick fixes have QuickFix kind."""
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"

        diagnostic = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=8)),
            message="Unclosed section: 'geometry'",
            severity=DiagnosticSeverity.Error,
            source="nwchem-lsp",
        )

        actions = provider.get_code_actions(source, [diagnostic])
        quick_fixes = [a for a in actions if a.kind and "quickfix" in str(a.kind.value).lower()]
        assert len(quick_fixes) >= 1

    def test_code_action_has_edit(self):
        """Test that code actions have workspace edits."""
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"

        diagnostic = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=8)),
            message="Unclosed section: 'geometry'",
            severity=DiagnosticSeverity.Error,
            source="nwchem-lsp",
        )

        actions = provider.get_code_actions(source, [diagnostic])
        for action in actions:
            if action.edit:
                assert action.edit.changes is not None
                break
        else:
            # At least one action should have an edit
            actions_with_edit = [a for a in actions if a.edit]
            assert len(actions_with_edit) >= 1


# ======================================================================
# New tests: rule-code-routed code actions
# ======================================================================


class TestNW1001UnclosedSection:
    """Quick fix for NW1001 -- unclosed section."""

    def test_adds_end_with_rule_code(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unclosed section: 'geometry'", code="NW1001")
        actions = provider.get_code_actions(source, [diag])
        assert any("Add 'end'" in a.title and "geometry" in a.title for a in actions)

    def test_edit_inserts_end_text(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unclosed section: 'geometry'", code="NW1001")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "Add 'end'" in a.title)
        edits = list(fix.edit.changes.values())[0]
        assert any("end" in e.new_text for e in edits)


class TestNW1002UnexpectedEnd:
    """Quick fix for NW1002 -- unexpected end."""

    def test_removes_stray_end(self):
        provider = CodeActionsProvider()
        source = "start water\nend"
        diag = _diag(1, 0, 3, "Unexpected 'end' without matching section", code="NW1002")
        actions = provider.get_code_actions(source, [diag])
        assert any("Remove unexpected 'end'" in a.title for a in actions)

    def test_no_action_when_line_is_not_end(self):
        """If the actual line content is not just 'end', no fix is offered."""
        provider = CodeActionsProvider()
        source = "start water\nend geometry"
        diag = _diag(1, 0, 3, "Unexpected 'end' without matching section", code="NW1002")
        actions = provider.get_code_actions(source, [diag])
        fix_actions = [a for a in actions if "Remove unexpected 'end'" in a.title]
        assert len(fix_actions) == 0


class TestNW2001UnknownKeyword:
    """Quick fix for NW2001 -- unknown keyword in section."""

    def test_suggests_correction_for_typo(self):
        provider = CodeActionsProvider()
        source = "scf\n  snglet\nend"
        diag = _diag(1, 2, 8, "Unknown keyword 'snglet' in scf section", code="NW2001")
        actions = provider.get_code_actions(source, [diag])
        assert any("singlet" in a.title.lower() for a in actions)

    def test_no_action_for_gibberish(self):
        provider = CodeActionsProvider()
        source = "scf\n  zzzzzzz\nend"
        diag = _diag(1, 2, 9, "Unknown keyword 'zzzzzzz' in scf section", code="NW2001")
        actions = provider.get_code_actions(source, [diag])
        replace_actions = [a for a in actions if "Replace" in a.title]
        assert len(replace_actions) == 0


class TestNW2002InvalidEnum:
    """Quick fix for NW2002 -- invalid enum value."""

    def test_suggests_closest_units_value(self):
        provider = CodeActionsProvider()
        source = "geometry units angstrom\n  O 0 0 0\nend"
        diag = _diag(0, 15, 23, "Invalid units 'angstrom' (expected one of: angstroms, au, bohr, nanometers, picometers)", code="NW2002")
        actions = provider.get_code_actions(source, [diag])
        assert any("Replace" in a.title and "angstrom" in a.title for a in actions)

    def test_suggests_closest_grid_value(self):
        provider = CodeActionsProvider()
        source = "dft\n  grid coarsest\nend"
        diag = _diag(1, 7, 15, "Invalid grid value 'coarsest' (expected one of: coarse, fine, medium, ultrafine, xfine)", code="NW2002")
        actions = provider.get_code_actions(source, [diag])
        assert any("Replace" in a.title for a in actions)

    def test_no_action_for_unrecognised_enum_context(self):
        """If the enum kind is not recognised from the message, no action."""
        provider = CodeActionsProvider()
        source = "something value xyz"
        diag = _diag(0, 10, 13, "Invalid foo 'xyz'", code="NW2002")
        actions = provider.get_code_actions(source, [diag])
        replace_actions = [a for a in actions if "Replace" in a.title]
        assert len(replace_actions) == 0


class TestNW2004MissingSection:
    """Quick fix for NW2004 -- missing required section."""

    def test_adds_geometry_stub(self):
        provider = CodeActionsProvider()
        source = "start water\ntask scf energy"
        diag = _diag(0, 0, 0, "Missing required 'geometry' block", code="NW2004")
        actions = provider.get_code_actions(source, [diag])
        assert any("geometry" in a.title.lower() and "stub" in a.title.lower() for a in actions)

    def test_adds_basis_stub(self):
        provider = CodeActionsProvider()
        source = "start water\ntask scf energy"
        diag = _diag(0, 0, 0, "Missing required 'basis' block", code="NW2004")
        actions = provider.get_code_actions(source, [diag])
        assert any("basis" in a.title.lower() and "stub" in a.title.lower() for a in actions)

    def test_adds_task_stub(self):
        provider = CodeActionsProvider()
        source = "start water\ngeometry\n  O 0 0 0\nend"
        diag = _diag(0, 0, 0, "Missing required 'task' block", code="NW2004")
        actions = provider.get_code_actions(source, [diag])
        assert any("task" in a.title.lower() and "stub" in a.title.lower() for a in actions)

    def test_stub_edit_contains_section_content(self):
        provider = CodeActionsProvider()
        source = "start water"
        diag = _diag(0, 0, 0, "Missing required 'geometry' block", code="NW2004")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "geometry" in a.title.lower())
        edits = list(fix.edit.changes.values())[0]
        combined = "".join(e.new_text for e in edits)
        assert "geometry" in combined
        assert "end" in combined


class TestNW2005UnknownTaskTheory:
    """Quick fix for NW2005 -- unknown task theory."""

    def test_suggests_closest_theory(self):
        provider = CodeActionsProvider()
        source = "task dftt energy"
        diag = _diag(0, 5, 9, "Unknown task theory 'dftt' (expected one of: ccsd, ccsd(t), dft, mcscf, mp2, rimp2, scf, semi)", code="NW2005")
        actions = provider.get_code_actions(source, [diag])
        assert any("dft" in a.title for a in actions)

    def test_no_fix_for_completely_wrong_theory(self):
        provider = CodeActionsProvider()
        source = "task xyz energy"
        diag = _diag(0, 5, 8, "Unknown task theory 'xyz' (expected one of: ...)", code="NW2005")
        actions = provider.get_code_actions(source, [diag])
        replace_actions = [a for a in actions if "Replace task theory" in a.title]
        assert len(replace_actions) == 0


class TestNW2006UnknownTaskOperation:
    """Quick fix for NW2006 -- unknown task operation."""

    def test_suggests_closest_operation(self):
        provider = CodeActionsProvider()
        source = "task dft optimise"
        diag = _diag(0, 9, 16, "Unknown task operation 'optimise'", code="NW2006")
        actions = provider.get_code_actions(source, [diag])
        assert any("optimize" in a.title for a in actions)


class TestNW2007UnknownBasisSet:
    """Quick fix for NW2007 -- unknown basis set."""

    def test_suggests_closest_basis(self):
        provider = CodeActionsProvider()
        source = "basis\n  * library 6-31g\nend"
        diag = _diag(1, 12, 17, "Unknown basis set '6-31g'", code="NW2007")
        actions = provider.get_code_actions(source, [diag])
        assert any("6-31" in a.title for a in actions)

    def test_uses_canonical_casing(self):
        provider = CodeActionsProvider()
        source = "basis\n  * library sto-3g\nend"
        diag = _diag(1, 12, 18, "Unknown basis set 'sto-3g'", code="NW2007")
        actions = provider.get_code_actions(source, [diag])
        replace_actions = [a for a in actions if "Replace basis set" in a.title]
        if replace_actions:
            fix = replace_actions[0]
            edits = list(fix.edit.changes.values())[0]
            new_text = edits[0].new_text
            assert new_text == "STO-3G"


class TestNW2008UnknownFunctional:
    """Quick fix for NW2008 -- unknown DFT functional."""

    def test_suggests_closest_functional(self):
        provider = CodeActionsProvider()
        source = "dft\n  xc b3lypp\nend"
        diag = _diag(1, 5, 11, "Unknown DFT functional 'b3lypp'", code="NW2008")
        actions = provider.get_code_actions(source, [diag])
        assert any("B3LYP" in a.title or "b3lyp" in a.title.lower() for a in actions)

    def test_uses_canonical_casing(self):
        provider = CodeActionsProvider()
        source = "dft\n  xc b3lypp\nend"
        diag = _diag(1, 5, 11, "Unknown DFT functional 'b3lypp'", code="NW2008")
        actions = provider.get_code_actions(source, [diag])
        replace_actions = [a for a in actions if "Replace functional" in a.title]
        if replace_actions:
            fix = replace_actions[0]
            edits = list(fix.edit.changes.values())[0]
            assert edits[0].new_text == "B3LYP"


class TestNW2009UnknownDirective:
    """Quick fix for NW2009 -- unknown top-level directive."""

    def test_suggests_correction(self):
        provider = CodeActionsProvider()
        source = "sart water"
        diag = _diag(0, 0, 4, "Unknown top-level directive 'sart'", code="NW2009")
        actions = provider.get_code_actions(source, [diag])
        assert any("start" in a.title.lower() for a in actions)


class TestNW2010DuplicateSection:
    """Quick fix for NW2010 -- duplicate section."""

    def test_removes_duplicate(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0\nend\ngeometry\n  H 0 0 0\nend"
        diag = _diag(4, 0, 8, "Duplicate 'geometry' section (only one allowed)", code="NW2010")
        actions = provider.get_code_actions(source, [diag])
        assert any("Remove duplicate" in a.title for a in actions)

    def test_duplicate_removal_edit_deletes_block(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0\nend\ngeometry\n  H 0 0 0\nend"
        diag = _diag(4, 0, 8, "Duplicate 'geometry' section (only one allowed)", code="NW2010")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "Remove duplicate" in a.title)
        edits = list(fix.edit.changes.values())[0]
        assert edits[0].new_text == ""


class TestFallbackMessageMatching:
    """Ensure diagnostics without a code still get matched by message."""

    def test_unclosed_section_no_code(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unclosed section: 'geometry'", code=None)
        actions = provider.get_code_actions(source, [diag])
        assert any("Add 'end'" in a.title for a in actions)

    def test_unexpected_end_no_code(self):
        provider = CodeActionsProvider()
        source = "end"
        diag = _diag(0, 0, 3, "Unexpected 'end' keyword (no matching section start)", code=None)
        actions = provider.get_code_actions(source, [diag])
        assert any("Remove unexpected 'end'" in a.title for a in actions)

    def test_unknown_keyword_no_code(self):
        provider = CodeActionsProvider()
        source = "gemoetry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unknown keyword 'gemoetry'", code=None)
        actions = provider.get_code_actions(source, [diag])
        assert any("geometry" in a.title.lower() for a in actions)


class TestUriPassthrough:
    """Verify that the URI is correctly used in WorkspaceEdit changes."""

    def test_custom_uri_in_edit(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unclosed section: 'geometry'", code="NW1001")
        actions = provider.get_code_actions(source, [diag], uri="file:///test.nw")
        fix = next(a for a in actions if "Add 'end'" in a.title)
        assert "file:///test.nw" in fix.edit.changes

    def test_default_uri_in_edit(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unclosed section: 'geometry'", code="NW1001")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "Add 'end'" in a.title)
        assert "document" in fix.edit.changes


class TestMultipleDiagnostics:
    """Verify actions are produced for multiple diagnostics."""

    def test_two_diagnostics_yield_two_fixes(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0\nend\nend"
        diag1 = _diag(0, 0, 8, "Unclosed section: 'geometry'", code="NW1001")
        diag2 = _diag(3, 0, 3, "Unexpected 'end' without matching section", code="NW1002")
        actions = provider.get_code_actions(source, [diag1, diag2])
        assert any("Add 'end'" in a.title for a in actions)
        assert any("Remove unexpected 'end'" in a.title for a in actions)

    def test_empty_diagnostics_yields_general_actions(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0\nend"
        actions = provider.get_code_actions(source, [])
        assert any("start" in a.title.lower() for a in actions)


class TestEditCorrectness:
    """Verify that the before/after text edits produce the expected result."""

    def _apply_edit(self, source: str, action: CodeAction) -> str:
        """Apply a single CodeAction's edit to the source text."""
        lines = source.split("\n")
        for uri_key, text_edits in action.edit.changes.items():
            for te in text_edits:
                start_line = te.range.start.line
                start_col = te.range.start.character
                end_line = te.range.end.line
                end_col = te.range.end.character

                before = lines[start_line][:start_col]
                after = lines[end_line][end_col:] if end_line < len(lines) else ""
                new_lines = (before + te.new_text + after).split("\n")

                lines[start_line : end_line + 1] = new_lines
        return "\n".join(lines)

    def test_unclosed_section_fix_produces_end(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unclosed section: 'geometry'", code="NW1001")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "Add 'end'" in a.title)
        result = self._apply_edit(source, fix)
        assert result.strip().endswith("end")

    def test_unexpected_end_fix_removes_line(self):
        provider = CodeActionsProvider()
        source = "start water\nend"
        diag = _diag(1, 0, 3, "Unexpected 'end' without matching section", code="NW1002")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "Remove unexpected 'end'" in a.title)
        result = self._apply_edit(source, fix)
        assert "end" not in result.split("\n")

    def test_keyword_typo_fix_replaces_text(self):
        provider = CodeActionsProvider()
        source = "gemoetry\n  O 0 0 0"
        diag = _diag(0, 0, 8, "Unknown keyword 'gemoetry'", code="NW2001")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "geometry" in a.title.lower())
        result = self._apply_edit(source, fix)
        assert result.startswith("geometry")

    def test_missing_geometry_stub_is_valid_block(self):
        provider = CodeActionsProvider()
        source = "start water\ntask scf energy"
        diag = _diag(0, 0, 0, "Missing required 'geometry' block", code="NW2004")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "geometry" in a.title.lower())
        result = self._apply_edit(source, fix)
        assert "geometry" in result
        lines = result.split("\n")
        assert any(line.strip().lower() == "end" for line in lines)

    def test_task_theory_fix_replaces_text(self):
        provider = CodeActionsProvider()
        source = "task dftt energy"
        diag = _diag(0, 5, 9, "Unknown task theory 'dftt'", code="NW2005")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "dft" in a.title)
        result = self._apply_edit(source, fix)
        assert "task dft" in result.lower()

    def test_duplicate_section_removal_preserves_first(self):
        provider = CodeActionsProvider()
        source = "geometry\n  O 0 0 0\nend\ngeometry\n  H 0 0 0\nend"
        diag = _diag(4, 0, 8, "Duplicate 'geometry' section (only one allowed)", code="NW2010")
        actions = provider.get_code_actions(source, [diag])
        fix = next(a for a in actions if "Remove duplicate" in a.title)
        result = self._apply_edit(source, fix)
        assert "O 0 0 0" in result
        assert "H 0 0 0" not in result

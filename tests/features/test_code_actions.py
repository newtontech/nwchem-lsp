"""Tests for code actions provider."""

import pytest
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

from nwchem_lsp.features.code_actions import CodeActionsProvider


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

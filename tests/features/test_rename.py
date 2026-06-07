"""Tests for rename provider."""

import pytest
from lsprotocol.types import Position

from nwchem_lsp.features.rename import RenameProvider, get_rename_provider


class TestRenameProvider:
    """Test rename provider."""

    @pytest.fixture
    def provider(self):
        """Create a rename provider."""
        return get_rename_provider()

    def test_get_rename_edits_valid(self, provider):
        """Test valid rename operation."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end

task dft
"""
        position = Position(line=2, character=0)
        edits = provider.get_rename_edits(text, "file:///test.nw", position, "basis")

        assert edits is not None
        assert "file:///test.nw" in edits.changes
        assert len(edits.changes["file:///test.nw"]) == 1
        assert edits.changes["file:///test.nw"][0].new_text == "basis"

    def test_get_rename_edits_not_section(self, provider):
        """Test rename when not on a section keyword."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end
"""
        position = Position(line=3, character=5)
        edits = provider.get_rename_edits(text, "file:///test.nw", position, "basis")

        assert edits is None

    def test_get_rename_edits_invalid_new_name(self, provider):
        """Test rename with invalid new name."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end
"""
        position = Position(line=2, character=0)
        edits = provider.get_rename_edits(text, "file:///test.nw", position, "invalid_keyword")

        assert edits is None

    def test_get_rename_edits_empty_document(self, provider):
        """Test rename for empty document."""
        position = Position(line=0, character=0)
        edits = provider.get_rename_edits("", "file:///test.nw", position, "basis")

        assert edits is None

    def test_is_valid_rename_true(self, provider):
        """Test valid rename check."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end
"""
        position = Position(line=2, character=0)
        assert provider.is_valid_rename(text, position, "basis") is True

    def test_is_valid_rename_false_not_section(self, provider):
        """Test invalid rename - not a section."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end
"""
        position = Position(line=3, character=5)
        assert provider.is_valid_rename(text, position, "basis") is False

    def test_is_valid_rename_false_invalid_new_name(self, provider):
        """Test invalid rename - invalid new name."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end
"""
        position = Position(line=2, character=0)
        assert provider.is_valid_rename(text, position, "invalid") is False

    def test_get_word_at_position(self, provider):
        """Test word extraction."""
        line = "geometry units angstroms"
        word = provider._get_word_at_position(line, 0)
        assert word == "geometry"

    def test_get_word_with_parentheses(self, provider):
        """Test word extraction with parentheses."""
        line = "ccsd(t)"
        word = provider._get_word_at_position(line, 0)
        assert word == "ccsd(t)"

    def test_provider_creation(self):
        """Test provider creation."""
        provider = RenameProvider()
        assert provider is not None
        assert provider.server is None

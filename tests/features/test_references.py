"""Tests for references provider."""

import pytest
from lsprotocol.types import Position

from nwchem_lsp.features.references import ReferencesProvider, get_references_provider


class TestReferencesProvider:
    """Test references provider."""

    @pytest.fixture
    def provider(self):
        """Create a references provider."""
        return get_references_provider()

    def test_get_references_geometry(self, provider):
        """Test getting references to geometry section."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end

task dft
"""
        position = Position(line=2, character=0)  # On "geometry"
        locations = provider.get_references(text, "file:///test.nw", position)

        assert len(locations) == 2  # geometry start + end
        assert locations[0].range.start.line == 2
        assert locations[1].range.start.line == 4

    def test_get_references_basis(self, provider):
        """Test getting references to basis section."""
        text = """start test

basis
  * library sto-3g
end

task scf
"""
        position = Position(line=2, character=0)
        locations = provider.get_references(text, "file:///test.nw", position)

        assert len(locations) == 2
        assert locations[0].range.start.line == 2
        assert locations[1].range.start.line == 4

    def test_get_references_not_on_keyword(self, provider):
        """Test getting references when not on a keyword."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end
"""
        position = Position(line=3, character=5)  # On coordinate line
        locations = provider.get_references(text, "file:///test.nw", position)

        assert len(locations) == 0

    def test_get_references_empty_document(self, provider):
        """Test getting references for empty document."""
        position = Position(line=0, character=0)
        locations = provider.get_references("", "file:///test.nw", position)

        assert len(locations) == 0

    def test_get_references_outside_range(self, provider):
        """Test getting references outside document range."""
        text = "start test\n"
        position = Position(line=100, character=0)
        locations = provider.get_references(text, "file:///test.nw", position)

        assert len(locations) == 0

    def test_get_references_multiple_sections(self, provider):
        """Test getting references with multiple sections."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end

basis
  * library sto-3g
end

dft
  xc b3lyp
end
"""
        position = Position(line=6, character=0)  # On "basis"
        locations = provider.get_references(text, "file:///test.nw", position)

        assert len(locations) == 2  # basis start + end
        assert locations[0].range.start.line == 6
        assert locations[1].range.start.line == 8

    def test_get_word_at_position(self, provider):
        """Test word extraction at position."""
        line = "geometry units angstroms"
        word = provider._get_word_at_position(line, 0)
        assert word == "geometry"

        word = provider._get_word_at_position(line, 3)
        assert word == "geometry"

    def test_get_word_with_parentheses(self, provider):
        """Test word extraction with parentheses (for ccsd(t))."""
        line = "ccsd(t)"
        word = provider._get_word_at_position(line, 0)
        assert word == "ccsd(t)"

    def test_provider_creation(self):
        """Test provider creation."""
        provider = ReferencesProvider()
        assert provider is not None
        assert provider.server is None

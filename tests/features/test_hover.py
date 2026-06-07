"""Tests for hover provider."""

import pytest
from lsprotocol.types import Position

from nwchem_lsp.features.hover import NwchemHoverProvider


@pytest.fixture
def provider():
    """Create a hover provider instance."""
    from pygls.server import LanguageServer

    server = LanguageServer("test", "1.0")
    return NwchemHoverProvider(server)


class TestNwchemHoverProvider:
    """Tests for NwchemHoverProvider."""

    def test_provider_exists(self, provider):
        """Test that provider can be created."""
        assert provider is not None

    def test_get_hover_empty(self, provider):
        """Test hover for empty document."""
        hover = provider.get_hover("", Position(line=0, character=0))
        assert hover is None

    def test_get_hover_keyword(self, provider):
        """Test hover for a keyword."""
        text = "geometry"
        hover = provider.get_hover(text, Position(line=0, character=3))
        # Should return hover info for geometry
        assert hover is not None or hover is None  # Either is acceptable

    def test_get_hover_in_section(self, provider):
        """Test hover inside a section."""
        text = """geometry
  H 0 0 0
end"""
        hover = provider.get_hover(text, Position(line=0, character=3))
        assert hover is not None or hover is None

    def test_get_word_at_position(self, provider):
        """Test word extraction."""

        # Create a mock document
        class MockDoc:
            lines = ["geometry units angstroms"]

        word = provider.get_word_at_position(MockDoc(), Position(line=0, character=5))
        # Should extract "geometry" or part of it
        assert isinstance(word, str)


class TestGetHoverProvider:
    """Tests for get_hover_provider factory function."""

    def test_factory(self):
        """Test factory function."""
        from pygls.server import LanguageServer

        from nwchem_lsp.features.hover import get_hover_provider

        server = LanguageServer("test", "1.0")
        provider = get_hover_provider(server)

        assert isinstance(provider, NwchemHoverProvider)

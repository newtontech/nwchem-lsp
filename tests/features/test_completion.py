"""Tests for completion provider."""

import pytest
from lsprotocol.types import Position

from nwchem_lsp.features.completion import NwchemCompletionProvider


@pytest.fixture
def provider():
    """Create a completion provider instance."""
    from pygls.server import LanguageServer
    server = LanguageServer("test", "1.0")
    return NwchemCompletionProvider(server)


class TestNwchemCompletionProvider:
    """Tests for NwchemCompletionProvider."""

    def test_provider_exists(self, provider):
        """Test that provider can be created."""
        assert provider is not None

    def test_get_completions_empty(self, provider):
        """Test completions for empty document."""
        completions = provider.get_completions("", Position(line=0, character=0))
        assert isinstance(completions, list)

    def test_get_completions_top_level(self, provider):
        """Test top-level keyword completions."""
        text = ""
        completions = provider.get_completions(text, Position(line=0, character=0))
        # Should return top-level keywords
        assert len(completions) > 0

    def test_get_completions_in_geometry(self, provider):
        """Test completions inside geometry block."""
        text = """geometry
  H 0 0 0
end
"""
        completions = provider.get_completions(text, Position(line=1, character=0))
        assert isinstance(completions, list)

    def test_get_dft_functional_completions(self, provider):
        """Test DFT functional completions."""
        text = """dft
  xc b
end
"""
        completions = provider.get_completions(text, Position(line=1, character=5))
        # Should include b3lyp and other B functionals
        assert isinstance(completions, list)

    def test_get_basis_set_completions(self, provider):
        """Test basis set completions."""
        text = """basis
  H library 6-
end
"""
        completions = provider.get_completions(text, Position(line=1, character=12))
        assert isinstance(completions, list)


class TestGetCompletionProvider:
    """Tests for get_completion_provider factory function."""

    def test_factory(self):
        """Test factory function."""
        from nwchem_lsp.features.completion import get_completion_provider
        from pygls.server import LanguageServer
        
        server = LanguageServer("test", "1.0")
        provider = get_completion_provider(server)
        
        assert isinstance(provider, NwchemCompletionProvider)

"""Tests for document symbols provider."""

import pytest
from lsprotocol.types import SymbolKind

from nwchem_lsp.features.symbols import NwchemSymbolProvider


@pytest.fixture
def provider():
    """Create a symbol provider instance."""
    from pygls.server import LanguageServer
    server = LanguageServer("test", "1.0")
    return NwchemSymbolProvider(server)


class TestNwchemSymbolProvider:
    """Tests for NwchemSymbolProvider."""

    def test_provider_exists(self, provider):
        """Test that provider can be created."""
        assert provider is not None

    def test_get_document_symbols_empty(self, provider):
        """Test symbols for empty document."""
        symbols = provider.get_document_symbols("")
        assert symbols == []

    def test_get_document_symbols_single_section(self, provider):
        """Test symbols for single section."""
        text = """geometry
  H 0 0 0
end
"""
        symbols = provider.get_document_symbols(text)
        assert len(symbols) == 1
        assert symbols[0].name == "GEOMETRY"
        assert symbols[0].kind == SymbolKind.Class

    def test_get_document_symbols_multiple_sections(self, provider):
        """Test symbols for multiple sections."""
        text = """geometry
  H 0 0 0
end

basis
  H library 6-31g
end

task scf
"""
        symbols = provider.get_document_symbols(text)
        assert len(symbols) >= 2
        
        names = [s.name.lower() for s in symbols]
        assert "geometry" in names
        assert "basis" in names

    def test_symbol_range(self, provider):
        """Test that symbol ranges are correct."""
        text = """geometry
  H 0 0 0
end
"""
        symbols = provider.get_document_symbols(text)
        assert len(symbols) == 1
        
        symbol = symbols[0]
        assert symbol.range.start.line == 0
        assert symbol.range.end.line >= 0

    def test_symbol_kind_mapping(self, provider):
        """Test that different sections get appropriate symbol kinds."""
        text = """geometry
  H 0 0 0
end

scf
  maxiter 100
end
"""
        symbols = provider.get_document_symbols(text)
        
        geometry_symbol = next((s for s in symbols if s.name == "GEOMETRY"), None)
        scf_symbol = next((s for s in symbols if s.name == "SCF"), None)
        
        if geometry_symbol:
            assert geometry_symbol.kind == SymbolKind.Class
        if scf_symbol:
            assert scf_symbol.kind == SymbolKind.Method

    def test_unclosed_section(self, provider):
        """Test handling of unclosed sections."""
        text = """geometry
  H 0 0 0
"""
        symbols = provider.get_document_symbols(text)
        # Should still create a symbol for the unclosed section
        assert len(symbols) >= 1
        assert symbols[0].name == "GEOMETRY"


class TestGetSymbolProvider:
    """Tests for get_symbol_provider factory function."""

    def test_factory(self):
        """Test factory function."""
        from nwchem_lsp.features.symbols import get_symbol_provider
        from pygls.server import LanguageServer
        
        server = LanguageServer("test", "1.0")
        provider = get_symbol_provider(server)
        
        assert isinstance(provider, NwchemSymbolProvider)

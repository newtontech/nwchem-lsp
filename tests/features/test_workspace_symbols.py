"""Tests for workspace symbols provider."""

import pytest
from lsprotocol.types import SymbolKind

from nwchem_lsp.features.workspace_symbols import WorkspaceSymbolProvider
from pygls.server import LanguageServer


class TestWorkspaceSymbolProvider:
    """Test workspace symbol provider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        server = LanguageServer("test", "0.1.0")
        return WorkspaceSymbolProvider(server)

    def test_provider_exists(self, provider):
        """Test provider can be created."""
        assert provider is not None

    def test_get_workspace_symbols_empty(self, provider):
        """Test with empty documents."""
        symbols = provider.get_workspace_symbols("", {})
        assert symbols == []

    def test_get_workspace_symbols_geometry(self, provider):
        """Test symbols for geometry section."""
        text = """start water

geometry units angstroms
  O 0 0 0
  H 1 0 0
  H 0 1 0
end

basis
  * library 6-31g*
end

task dft optimize
"""
        documents = {"file://test.nw": text}
        symbols = provider.get_workspace_symbols("", documents)

        assert len(symbols) >= 2  # geometry and basis

        # Check geometry symbol
        geo_symbols = [s for s in symbols if s.name == "GEOMETRY"]
        assert len(geo_symbols) == 1
        assert geo_symbols[0].kind == SymbolKind.Class

    def test_get_workspace_symbols_with_query(self, provider):
        """Test symbols with search query."""
        text = """start test

geometry
  H 0 0 0
end

dft
  xc b3lyp
end
"""
        documents = {"file://test.nw": text}
        symbols = provider.get_workspace_symbols("dft", documents)

        # Should only return DFT-related symbols
        assert len(symbols) >= 1
        assert any(s.name == "DFT" for s in symbols)

    def test_get_workspace_symbols_no_match(self, provider):
        """Test with query that matches nothing."""
        text = """start test
geometry
  H 0 0 0
end
"""
        documents = {"file://test.nw": text}
        symbols = provider.get_workspace_symbols("xyzabc", documents)
        assert len(symbols) == 0

    def test_symbol_container_name(self, provider):
        """Test symbol container name."""
        text = """geometry
  H 0 0 0
end
"""
        documents = {"file://test.nw": text}
        symbols = provider.get_workspace_symbols("", documents)

        assert len(symbols) >= 1
        assert symbols[0].container_name == "NWChem Input"

    def test_multiple_documents(self, provider):
        """Test with multiple documents."""
        doc1 = """geometry
  O 0 0 0
end
"""
        doc2 = """basis
  * library sto-3g
end
"""
        documents = {
            "file://doc1.nw": doc1,
            "file://doc2.nw": doc2,
        }
        symbols = provider.get_workspace_symbols("", documents)

        # Should have symbols from both documents
        assert len(symbols) >= 2

    def test_resolve_workspace_symbol(self, provider):
        """Test symbol resolution."""
        from lsprotocol.types import WorkspaceSymbol, Location, Range, Position

        symbol = WorkspaceSymbol(
            name="TEST",
            kind=SymbolKind.Class,
            location=Location(
                uri="file://test.nw",
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=0, character=4),
                ),
            ),
        )
        resolved = provider.resolve_workspace_symbol(symbol)
        assert resolved is not None

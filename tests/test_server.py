"""Tests for NWChem LSP server."""
import pytest
from unittest.mock import MagicMock, patch

from nwchem_lsp.server import server, main


class TestNWChemServer:
    """Test NWChem LSP server."""

    def test_server_exists(self):
        """Test server instance exists."""
        assert server is not None
        assert server.name == "nwchem-lsp"
        assert server.version == "0.1.0"

    def test_completion_feature(self):
        """Test completion feature."""
        from nwchem_lsp.server import completion
        result = completion(MagicMock())
        assert result == []

    def test_hover_feature(self):
        """Test hover feature."""
        from nwchem_lsp.server import hover
        result = hover(MagicMock())
        assert result is None

    def test_diagnostic_feature(self):
        """Test diagnostic feature."""
        from nwchem_lsp.server import diagnostic
        result = diagnostic(MagicMock())
        assert result == []


class TestMain:
    """Test main entry point."""

    @patch('nwchem_lsp.server.server.start_io')
    def test_main(self, mock_start):
        """Test main function."""
        main()
        mock_start.assert_called_once()

    @patch('nwchem_lsp.server.server.start_io')
    def test_main_module(self, mock_start):
        """Test main as module."""
        import nwchem_lsp.server as server_module
        server_module.main()
        mock_start.assert_called_once()

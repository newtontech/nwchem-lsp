"""Tests for NWChem LSP server."""

from unittest.mock import MagicMock, patch

import pytest

from nwchem_lsp.server import create_server, main, server


class TestNWChemServer:
    """Test NWChem LSP server."""

    def test_server_exists(self):
        """Test server instance exists."""
        assert server is not None
        assert server.name == "nwchem-lsp"
        assert server.version == "0.3.0"

    def test_create_server(self):
        """Test create_server function."""
        srv = create_server()
        assert srv is not None
        assert srv.name == "nwchem-lsp"

    def test_completion_provider(self):
        """Test completion provider exists."""
        srv = create_server()
        assert hasattr(srv, "completion_provider")

    def test_hover_provider(self):
        """Test hover provider exists."""
        srv = create_server()
        assert hasattr(srv, "hover_provider")

    def test_diagnostic_provider(self):
        """Test diagnostic provider exists."""
        srv = create_server()
        assert hasattr(srv, "diagnostic_provider")


class TestMain:
    """Test main entry point."""

    @patch("nwchem_lsp.server.server.start_io")
    def test_main(self, mock_start):
        """Test main function."""
        main()
        mock_start.assert_called_once()

    @patch("nwchem_lsp.server.server.start_io")
    def test_main_module(self, mock_start):
        """Test main as module."""
        import nwchem_lsp.server as server_module

        server_module.main()
        mock_start.assert_called_once()

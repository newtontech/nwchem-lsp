"""Tests for diagnostic providers."""

import pytest

from nwchem_lsp.features.diagnostic import DiagnosticProvider
from nwchem_lsp.features.diagnostics import DiagnosticsProvider


@pytest.fixture
def diagnostic_provider():
    """Create a diagnostic provider instance."""
    from pygls.server import LanguageServer
    server = LanguageServer("test", "1.0")
    return DiagnosticProvider(server)


@pytest.fixture
def diagnostics_provider():
    """Create a diagnostics provider instance."""
    return DiagnosticsProvider()


class TestDiagnosticProvider:
    """Tests for DiagnosticProvider."""

    def test_provider_exists(self, diagnostic_provider):
        """Test that provider can be created."""
        assert diagnostic_provider is not None

    def test_get_diagnostics_empty(self, diagnostic_provider):
        """Test diagnostics for empty document."""
        diagnostics = diagnostic_provider.get_diagnostics("")
        assert isinstance(diagnostics, list)

    def test_get_diagnostics_valid(self, diagnostic_provider):
        """Test diagnostics for valid input."""
        text = """geometry
  H 0 0 0
end

basis
  H library 6-31g
end

task scf energy
"""
        diagnostics = diagnostic_provider.get_diagnostics(text)
        assert isinstance(diagnostics, list)

    def test_get_diagnostics_missing_geometry(self, diagnostic_provider):
        """Test detection of missing geometry."""
        text = """basis
  H library 6-31g
end"""
        diagnostics = diagnostic_provider.get_diagnostics(text)
        # Should report missing geometry
        messages = [d.message for d in diagnostics]
        assert any("geometry" in m.lower() for m in messages)


class TestDiagnosticsProvider:
    """Tests for DiagnosticsProvider."""

    def test_provider_exists(self, diagnostics_provider):
        """Test that provider can be created."""
        assert diagnostics_provider is not None

    def test_get_diagnostics_empty(self, diagnostics_provider):
        """Test diagnostics for empty source."""
        diagnostics = diagnostics_provider.get_diagnostics("")
        assert isinstance(diagnostics, list)

    def test_get_diagnostics_valid(self, diagnostics_provider):
        """Test diagnostics for valid source."""
        text = """geometry
  H 0 0 0
end"""
        diagnostics = diagnostics_provider.get_diagnostics(text)
        assert isinstance(diagnostics, list)

    def test_check_line_empty(self, diagnostics_provider):
        """Test checking empty line."""
        diagnostics = diagnostics_provider._check_line("", 0)
        assert diagnostics == []

    def test_check_line_comment(self, diagnostics_provider):
        """Test checking comment line."""
        diagnostics = diagnostics_provider._check_line("# This is a comment", 0)
        assert diagnostics == []

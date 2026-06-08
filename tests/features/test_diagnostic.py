"""Tests for diagnostic providers."""

import json

import pytest

from nwchem_lsp.features.diagnostic import DiagnosticProvider


@pytest.fixture
def diagnostic_provider():
    """Create a diagnostic provider instance."""
    from pygls.server import LanguageServer

    server = LanguageServer("test", "1.0")
    return DiagnosticProvider(server)


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Snapshot tests
# ---------------------------------------------------------------------------

VALID_INPUT = """\
geometry
  H 0 0 0
end

basis
  H library 6-31g
end

task scf energy
"""

INPUT_WITH_WARNINGS = """\
geometry
  H 0 0 0
end

basis
  H library fake-basis
end

task scf energy
"""

INPUT_WITH_ERRORS = """\
geometry
  H 0 0 0
end

basis
  H library 6-31g
end

task badtheory energy
"""


class TestDiagnosticsSnapshot:
    """Tests for the diagnostics snapshot feature."""

    # -- get_diagnostics_snapshot (per-URI) --

    def test_snapshot_empty_cache(self, diagnostic_provider):
        """Snapshot returns [] for a URI that was never cached."""
        snapshot = diagnostic_provider.get_diagnostics_snapshot("file:///unknown.nw")
        assert snapshot == []

    def test_snapshot_valid_document(self, diagnostic_provider):
        """Snapshot for a clean document is empty (no diagnostics)."""
        uri = "file:///test.nw"
        diags = diagnostic_provider.get_diagnostics(VALID_INPUT)
        diagnostic_provider.update_cache(uri, diags)

        snapshot = diagnostic_provider.get_diagnostics_snapshot(uri)
        assert snapshot == []

    def test_snapshot_document_with_warnings(self, diagnostic_provider):
        """Snapshot captures warnings with correct severity."""
        uri = "file:///warn.nw"
        diags = diagnostic_provider.get_diagnostics(INPUT_WITH_WARNINGS)
        diagnostic_provider.update_cache(uri, diags)

        snapshot = diagnostic_provider.get_diagnostics_snapshot(uri)
        assert len(snapshot) >= 1
        # Find the entry from the original diagnostic provider (no code)
        entry = next(e for e in snapshot if "fake-basis" in e["message"] and e.get("code") is None)
        assert entry["severity"] == 2  # DiagnosticSeverity.Warning
        assert entry["severity_label"] == "warning"
        assert entry["source"] == "nwchem-lsp"
        assert entry["source"] == "nwchem-lsp"
        assert isinstance(entry["range"], dict)
        assert "start" in entry["range"] and "end" in entry["range"]

    def test_snapshot_document_with_errors(self, diagnostic_provider):
        """Snapshot captures errors with correct severity."""
        uri = "file:///err.nw"
        diags = diagnostic_provider.get_diagnostics(INPUT_WITH_ERRORS)
        diagnostic_provider.update_cache(uri, diags)

        snapshot = diagnostic_provider.get_diagnostics_snapshot(uri)
        assert len(snapshot) >= 1
        # Find the entry from the original diagnostic provider (no code)
        entry = next(e for e in snapshot if "badtheory" in e["message"] and e.get("code") is None)
        assert entry["severity"] == 1  # DiagnosticSeverity.Error
        assert entry["severity_label"] == "error"

    def test_snapshot_fields_present(self, diagnostic_provider):
        """Every snapshot entry has all required fields."""
        uri = "file:///fields.nw"
        diags = diagnostic_provider.get_diagnostics(INPUT_WITH_ERRORS)
        diagnostic_provider.update_cache(uri, diags)

        snapshot = diagnostic_provider.get_diagnostics_snapshot(uri)
        assert len(snapshot) >= 1
        required_keys = {"range", "severity", "severity_label", "source", "code", "message"}
        for entry in snapshot:
            assert required_keys.issubset(entry.keys())

    def test_snapshot_updates_after_change(self, diagnostic_provider):
        """Snapshot reflects the latest diagnostics after a cache update."""
        uri = "file:///update.nw"

        # First: valid document => no diagnostics
        diags = diagnostic_provider.get_diagnostics(VALID_INPUT)
        diagnostic_provider.update_cache(uri, diags)
        assert diagnostic_provider.get_diagnostics_snapshot(uri) == []

        # Now: introduce errors
        diags = diagnostic_provider.get_diagnostics(INPUT_WITH_ERRORS)
        diagnostic_provider.update_cache(uri, diags)
        snapshot = diagnostic_provider.get_diagnostics_snapshot(uri)
        assert len(snapshot) >= 1
        assert any(e["severity_label"] == "error" for e in snapshot)

    # -- get_all_snapshots --

    def test_get_all_snapshots_empty(self, diagnostic_provider):
        """get_all_snapshots returns {} when nothing is cached."""
        assert diagnostic_provider.get_all_snapshots() == {}

    def test_get_all_snapshots_multiple_uris(self, diagnostic_provider):
        """get_all_snapshots returns per-URI entries for all cached docs."""
        uri_a = "file:///a.nw"
        uri_b = "file:///b.nw"

        diags_a = diagnostic_provider.get_diagnostics(VALID_INPUT)
        diagnostic_provider.update_cache(uri_a, diags_a)

        diags_b = diagnostic_provider.get_diagnostics(INPUT_WITH_ERRORS)
        diagnostic_provider.update_cache(uri_b, diags_b)

        all_snapshots = diagnostic_provider.get_all_snapshots()
        assert set(all_snapshots.keys()) == {uri_a, uri_b}
        assert all_snapshots[uri_a] == []
        assert len(all_snapshots[uri_b]) >= 1

    # -- snapshot_to_json --

    def test_snapshot_to_json_single_uri(self, diagnostic_provider):
        """snapshot_to_json with a URI produces valid, deterministic JSON."""
        uri = "file:///json.nw"
        diags = diagnostic_provider.get_diagnostics(INPUT_WITH_WARNINGS)
        diagnostic_provider.update_cache(uri, diags)

        json_str = diagnostic_provider.snapshot_to_json(uri)
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1
        assert any("fake-basis" in e["message"] for e in parsed)

    def test_snapshot_to_json_all_uris(self, diagnostic_provider):
        """snapshot_to_json without a URI produces a JSON object keyed by URI."""
        uri = "file:///jsonall.nw"
        diags = diagnostic_provider.get_diagnostics(INPUT_WITH_ERRORS)
        diagnostic_provider.update_cache(uri, diags)

        json_str = diagnostic_provider.snapshot_to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert uri in parsed
        assert len(parsed[uri]) >= 1

    def test_snapshot_json_deterministic(self, diagnostic_provider):
        """Calling snapshot_to_json twice yields identical output."""
        uri = "file:///det.nw"
        diags = diagnostic_provider.get_diagnostics(INPUT_WITH_WARNINGS)
        diagnostic_provider.update_cache(uri, diags)

        first = diagnostic_provider.snapshot_to_json(uri)
        second = diagnostic_provider.snapshot_to_json(uri)
        assert first == second

    # -- _diagnostic_to_dict edge cases --

    def test_diagnostic_dict_code_none(self, diagnostic_provider):
        """_diagnostic_to_dict handles None code gracefully."""
        from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

        diag = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
            message="test",
            severity=DiagnosticSeverity.Information,
            source="nwchem-lsp",
        )
        result = diagnostic_provider._diagnostic_to_dict(diag)
        assert result["code"] is None
        assert result["severity_label"] == "information"

    def test_diagnostic_dict_severity_none_defaults_to_error(self, diagnostic_provider):
        """When severity is None, it defaults to Error."""
        from lsprotocol.types import Diagnostic, Position, Range

        diag = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
            message="no severity",
        )
        result = diagnostic_provider._diagnostic_to_dict(diag)
        assert result["severity"] == 1  # Error
        assert result["severity_label"] == "error"

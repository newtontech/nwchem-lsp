"""Tests for the agent API provider."""

import json
import pytest

from nwchem_lsp.features.agent_api import AgentAPIProvider, AgentAPISnapshot


@pytest.fixture
def provider() -> AgentAPIProvider:
    return AgentAPIProvider()


class TestAgentAPISnapshot:
    def test_to_json(self):
        s = AgentAPISnapshot(uri="test.nw", diagnostics=[{"line": 0, "message": "test"}])
        data = json.loads(s.to_json())
        assert data["uri"] == "test.nw"
        assert len(data["diagnostics"]) == 1

    def test_empty(self):
        s = AgentAPISnapshot()
        data = json.loads(s.to_json())
        assert data["diagnostics"] == []


class TestAgentAPIProvider:
    def test_snapshot_with_empty_source(self, provider: AgentAPIProvider):
        snap = provider.get_snapshot("")
        assert snap.uri == ""
        assert isinstance(snap.diagnostics, list)

    def test_snapshot_with_source(self, provider: AgentAPIProvider):
        source = "title test\nstart\n  task scf\nend\n"
        snap = provider.get_snapshot(source, uri="file:///test.nw")
        assert snap.uri == "file:///test.nw"
        assert snap.metadata["language"] == "nwchem"
        assert len(snap.outline) > 0

    def test_outline_sections(self, provider: AgentAPIProvider):
        source = "geometry\n  O 0 0 0\nend\nbasis\n  O library 6-31g\nend\n"
        snap = provider.get_snapshot(source)
        sections = [o for o in snap.outline if o["type"] == "section"]
        section_names = [s["name"] for s in sections]
        assert "geometry" in section_names
        assert "basis" in section_names

    def test_diagnostics_json(self, provider: AgentAPIProvider):
        result = provider.get_diagnostics_json("title test\n")
        data = json.loads(result)
        assert "diagnostics" in data
        assert "count" in data

    def test_outline_json(self, provider: AgentAPIProvider):
        result = provider.get_outline_json("task scf\n")
        data = json.loads(result)
        assert "outline" in data

    def test_metadata(self, provider: AgentAPIProvider):
        snap = provider.get_snapshot("title test\n")
        assert snap.metadata["provider"] == "nwchem-lsp"
        assert "diagnostics" in snap.metadata["feature_count"]

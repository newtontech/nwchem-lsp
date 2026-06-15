"""Closed-loop fixture tests for agent CLI and DiagnosticEnvelope/v1 (issue #95)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nwchem_lsp import tool
from nwchem_lsp.features.agent_api import AgentAPIProvider

FIXTURES = Path(__file__).parent / "fixtures"
LOG_FIXTURES = FIXTURES / "logs"


class TestDiagnosticEnvelopeV1:
    def test_valid_fixture_has_no_blocking_diagnostics(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "valid" / "water_scf.nw")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["diagnostic_envelope"] == "v1"
        blocking = [d for d in payload["diagnostics"] if d.get("blocking")]
        assert blocking == []

    def test_invalid_missing_required_has_blocking_error(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "invalid" / "missing_required.nw")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is False
        blocking = [d for d in payload["diagnostics"] if d.get("blocking")]
        assert len(blocking) >= 1

    def test_invalid_unknown_keyword_has_advisory(self, capsys) -> None:
        rc = tool.main(["check", str(FIXTURES / "invalid" / "unknown_keyword.nw")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        advisory = [
            d
            for d in payload["diagnostics"]
            if d.get("severity") in {"warning", "hint", "information"}
        ]
        assert advisory, "expected advisory diagnostic for unknown keyword"


class TestFixOperation:
    def test_fix_returns_preview_actions(self, capsys) -> None:
        rc = tool.main(["fix", str(FIXTURES / "invalid" / "missing_required.nw")])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["capabilities"]["operation"] == "fix"
        assert isinstance(payload["actions"], list)


class TestOutputLogDiagnostics:
    def test_parse_log_fixture_detects_scf_failure(self) -> None:
        text = (LOG_FIXTURES / "scf_not_converged.out").read_text(encoding="utf-8")
        findings = AgentAPIProvider.parse_log(text)
        assert any(f["code"] == "NWCHEM-E044" for f in findings)

    def test_parse_log_fixture_detects_scf_energy(self) -> None:
        text = (LOG_FIXTURES / "scf_converged.out").read_text(encoding="utf-8")
        findings = AgentAPIProvider.parse_log(text)
        assert any(f["code"] == "NWCHEM-INFO-001" for f in findings)


class TestOpenQCSmokeEvidence:
    def test_capabilities_file_lists_output_log_patterns(self) -> None:
        caps = json.loads(
            (Path(__file__).parent.parent / "lsp-capabilities.json").read_text(encoding="utf-8")
        )
        assert len(caps.get("outputLogPatterns", [])) >= 1
        assert len(caps.get("sourceProvenance", [])) >= 2

    def test_openqc_smoke_passes(self) -> None:
        result = AgentAPIProvider.openqc_smoke()
        assert result["status"] == "pass"

    def test_manifest_operation_works(self, capsys) -> None:
        rc = tool.main(["manifest"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "capabilities" in payload

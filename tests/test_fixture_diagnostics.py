"""Closed-loop tests running diagnostics on every fixture in fixtures/.

Each fixture is loaded, diagnostics are collected, and the result is compared
against the expected outcomes declared in fixtures/manifest.json.  Tests fail
if a valid fixture produces false positives, an invalid fixture produces no
diagnostics, or the envelope metadata (rule_id, blocking, source_provenance)
does not match the manifest.
"""

from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock

import pytest

from nwchem_lsp.features.diagnostic import (
    RULE_REGISTRY,
    DiagnosticEnvelope,
    FixPreview,
    NwchemDiagnosticProvider,
)

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent.parent / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"


def _load_manifest() -> dict:
    with open(MANIFEST_PATH) as fh:
        return json.load(fh)


def _read_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text()


def _make_provider() -> NwchemDiagnosticProvider:
    mock_server = MagicMock()
    return NwchemDiagnosticProvider(mock_server)


MANIFEST = _load_manifest()


class TestFixtureDiagnostics:
    """Run diagnostics on every fixture and validate against manifest."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.provider = _make_provider()

    def _get_diagnostic_texts(self, text: str):
        diags = self.provider.get_diagnostics(text)
        return diags

    def _get_envelope_dicts(self, text: str):
        diags = self._get_diagnostic_texts(text)
        envelopes = [self.provider.to_envelope(d) for d in diags]
        return [e.to_dict() for e in envelopes]

    @pytest.mark.parametrize(
        "fixture_entry",
        MANIFEST["fixtures"],
        ids=[f["file"] for f in MANIFEST["fixtures"]],
    )
    def test_fixture_diagnostics_vs_manifest(self, fixture_entry):
        text = _read_fixture(fixture_entry["file"])
        envelopes = self._get_envelope_dicts(text)

        expected_diags = fixture_entry["expected_diagnostics"]
        expected_severity = fixture_entry["expected_severity"]

        if expected_severity == "clean":
            assert len(envelopes) == 0, (
                f"Expected no diagnostics for {fixture_entry['file']}, "
                f"got {len(envelopes)}: {[e['message'] for e in envelopes]}"
            )
            return

        assert len(envelopes) > 0, (
            f"Expected at least one diagnostic for {fixture_entry['file']}, got none"
        )

        for expected in expected_diags:
            matching = [
                e
                for e in envelopes
                if e["rule_id"] == expected["rule_id"]
                and expected["message_contains"].lower() in e["message"].lower()
            ]
            assert len(matching) >= 1, (
                f"No diagnostic with rule_id={expected['rule_id']} and "
                f"message containing '{expected['message_contains']}' "
                f"in {fixture_entry['file']}. "
                f"Got: {[{'rule_id': e['rule_id'], 'msg': e['message']} for e in envelopes]}"
            )

            diag_env = matching[0]

            if expected.get("severity") == "error":
                assert diag_env["severity"] == 1
                assert diag_env["severity_label"] == "error"
            elif expected.get("severity") == "warning":
                assert diag_env["severity"] == 2
                assert diag_env["severity_label"] == "warning"

            assert diag_env["blocking"] == expected.get("blocking", False), (
                f"blocking mismatch for {expected['rule_id']} in {fixture_entry['file']}"
            )

            assert diag_env["rule_id"] == expected["rule_id"]
            assert diag_env["source"] == "nwchem-lsp"

    @pytest.mark.parametrize(
        "fixture_entry",
        [f for f in MANIFEST["fixtures"] if f["role"] == "valid"],
        ids=[f["file"] for f in MANIFEST["fixtures"] if f["role"] == "valid"],
    )
    def test_valid_fixtures_have_no_false_positives(self, fixture_entry):
        text = _read_fixture(fixture_entry["file"])
        envelopes = self._get_envelope_dicts(text)
        assert envelopes == [], (
            f"Valid fixture {fixture_entry['file']} produced false positives: "
            f"{[e['message'] for e in envelopes]}"
        )


class TestDiagnosticEnvelopeV1:
    """Validate DiagnosticEnvelope/v1 schema and FixPreview."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.provider = _make_provider()

    def test_envelope_schema_fields(self):
        text = _read_fixture("invalid_unknown_theory.nw")
        diags = self.provider.get_diagnostics(text)
        assert len(diags) > 0

        env = self.provider.to_envelope(diags[0])
        d = env.to_dict()

        required_fields = [
            "range",
            "message",
            "severity",
            "severity_label",
            "source",
            "code",
            "rule_id",
            "blocking",
            "source_provenance",
            "version_scope",
        ]
        for field_name in required_fields:
            assert field_name in d, f"Missing required field: {field_name}"

        assert d["rule_id"] == "NW001"
        assert d["blocking"] is True
        assert d["source_provenance"] == "https://nwchemgit.github.io/Task.html"
        assert d["source"] == "nwchem-lsp"

    def test_envelope_fix_preview_present_for_nw001(self):
        text = _read_fixture("invalid_unknown_theory.nw")
        diags = self.provider.get_diagnostics(text)
        env = self.provider.to_envelope(diags[0])
        d = env.to_dict()

        assert "fix_preview" in d
        fp = d["fix_preview"]
        assert fp["rule_id"] == "NW001"
        assert fp["action"] == "replace"
        assert fp["replacement"] == "scf"
        assert "scf" in fp["alternatives"]
        assert "dft" in fp["alternatives"]

    def test_envelope_fix_preview_present_for_nw003(self):
        text = _read_fixture("warning_unknown_basis.nw")
        diags = self.provider.get_diagnostics(text)
        env = self.provider.to_envelope(diags[0])
        d = env.to_dict()

        assert "fix_preview" in d
        fp = d["fix_preview"]
        assert fp["rule_id"] == "NW003"
        assert fp["action"] == "replace"
        assert fp["replacement"] == "sto-3g"

    def test_envelope_fix_preview_present_for_nw004(self):
        text = _read_fixture("invalid_unknown_operation.nw")
        diags = self.provider.get_diagnostics(text)
        env = self.provider.to_envelope(diags[0])
        d = env.to_dict()

        assert "fix_preview" in d
        fp = d["fix_preview"]
        assert fp["rule_id"] == "NW004"
        assert fp["action"] == "replace"
        assert fp["replacement"] == "energy"

    def test_envelope_fix_preview_present_for_nw005(self):
        text = _read_fixture("invalid_bad_functional.nw")
        diags = self.provider.get_diagnostics(text)
        env = self.provider.to_envelope(diags[0])
        d = env.to_dict()

        assert "fix_preview" in d
        fp = d["fix_preview"]
        assert fp["rule_id"] == "NW005"
        assert fp["action"] == "replace"
        assert fp["replacement"] == "b3lyp"

    def test_envelope_fix_preview_none_for_nw002(self):
        text = _read_fixture("invalid_missing_geometry.nw")
        diags = self.provider.get_diagnostics(text)
        matching = [d for d in diags if "geometry" in d.message.lower()]
        assert len(matching) > 0

        env = self.provider.to_envelope(matching[0])
        d = env.to_dict()

        assert "fix_preview" in d
        fp = d["fix_preview"]
        assert fp["action"] == "insert"
        assert "geometry" in fp["replacement"].lower()

    def test_to_dict_deterministic_order(self):
        text = _read_fixture("invalid_unknown_theory.nw")
        diags = self.provider.get_diagnostics(text)

        d1 = self.provider.to_envelope(diags[0]).to_dict()
        d2 = self.provider.to_envelope(diags[0]).to_dict()
        assert d1 == d2

    def test_rule_registry_completeness(self):
        expected_rules = {"NW000", "NW001", "NW002", "NW003", "NW004", "NW005", "NW006", "NW007", "NW008", "NW009"}
        actual_rules = set(RULE_REGISTRY.keys())
        assert expected_rules == actual_rules, (
            f"Rule registry mismatch: expected={expected_rules}, actual={actual_rules}"
        )

    def test_all_rules_have_required_fields(self):
        required_fields = {"description", "severity", "blocking", "source_provenance", "version_scope"}
        for rule_id, meta in RULE_REGISTRY.items():
            for field_name in required_fields:
                assert field_name in meta, f"Rule {rule_id} missing field: {field_name}"

    def test_assign_rule_id_unknown_message(self):
        result = NwchemDiagnosticProvider._assign_rule_id("some completely unknown message")
        assert result == "NW000"

    def test_snapshot_json_valid(self):
        text = _read_fixture("invalid_unknown_theory.nw")
        diags = self.provider.get_diagnostics(text)
        self.provider.update_cache("test://file.nw", diags)

        snapshot = self.provider.snapshot_to_json("test://file.nw")
        parsed = json.loads(snapshot)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_fix_preview_dataclass_to_dict(self):
        fp = FixPreview(
            rule_id="NW001",
            description="Replace theory",
            action="replace",
            range={"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
            replacement="scf",
            alternatives=["scf", "dft"],
        )
        d = fp.to_dict()
        assert d["rule_id"] == "NW001"
        assert d["action"] == "replace"
        assert d["alternatives"] == ["scf", "dft"]

"""Tests for the universal generated-input preflight surface (issue #91).

These tests pin the ``DiagnosticEnvelope/v1`` contract, the generic
artifact-role cross-block graph, the agent CLI wiring (``check``/``preflight``/
``manifest``), and the per-fixture regression expectations. They mirror the
abacus/gamess preflight test shape so the parent ``bohrium_skills`` probe can
treat nwchem-lsp as one more participant in the fleet-wide preflight contract.
"""

from __future__ import annotations

import json
from pathlib import Path

from nwchem_lsp.preflight import (
    ALL_ROLES,
    CODE_DFT_WITHOUT_FUNCTIONAL,
    CODE_ECP_WITHOUT_BASIS,
    CODE_LOW_MEMORY,
    CODE_MISSING_BASIS,
    CODE_MISSING_BLOCK,
    CODE_STRUCTURE_EMPTY,
    CODE_TASK_BASIS_MISMATCH,
    CODE_TASK_WITHOUT_SECTION,
    CODE_THEORY_BASIS_MISMATCH,
    CODE_VERSION_ASSUMPTION,
    DEFAULT_MEMORY_WARNING_MB,
    fleet_manifest,
    looks_like_nwchem_workspace,
    preflight_diagnostics,
    resolve_version_assumption,
)
from nwchem_lsp.rich_diagnostics import (
    DIAGNOSTIC_ENGINE_VERSION,
    DIAGNOSTIC_ENVELOPE_VERSION,
    agent_check_payload,
)
from nwchem_lsp.tool import SOFTWARE, check_path, manifest_path, preflight_path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "preflight"


# --------------------------------------------------------------------------- #
# DiagnosticEnvelope/v1 contract                                              #
# --------------------------------------------------------------------------- #


def test_envelope_version_constant_matches_v1() -> None:
    assert DIAGNOSTIC_ENVELOPE_VERSION == "v1"


def test_agent_payload_carries_envelope_top_level_fields() -> None:
    payload = agent_check_payload(
        software=SOFTWARE,
        uri="file:///tmp/input.nw",
        diagnostics=[],
    )
    assert payload["diagnostic_engine"] == DIAGNOSTIC_ENGINE_VERSION
    assert payload["diagnostic_envelope"] == DIAGNOSTIC_ENVELOPE_VERSION
    assert payload["ok"] is True
    assert payload["summary"]["count"] == 0


def test_manifest_shape_is_machine_readable() -> None:
    manifest = fleet_manifest()
    assert manifest["software"] == SOFTWARE
    assert manifest["preflight_envelope"] == "DiagnosticEnvelope/v1"
    assert manifest["artifact_roles"] == list(ALL_ROLES)
    for capability in (
        "version-aware-keywords",
        "cross-artifact-graph",
        "code-actions",
        "fleet-regression-fixtures",
    ):
        assert manifest["capabilities"][capability]["status"] == "available"
    # Every evidence code in the manifest must resolve to a documented entry.
    for code, entry in manifest["codes"].items():
        assert entry["severity"] in {"error", "warning", "information"}
        assert entry["capability"] in manifest["capabilities"]


def test_resolve_version_assumption_defaults_to_unknown() -> None:
    assumption = resolve_version_assumption(None)
    assert assumption["software"] == SOFTWARE
    assert assumption["software_version"] == "unknown"
    assert assumption["runtime_image"] == "unknown"
    assert assumption["exact_runtime_known"] is False
    assert assumption["declared_by"] == "fallback"


def test_resolve_version_assumption_respects_intent() -> None:
    assumption = resolve_version_assumption(
        {"software_version": "7.2.0", "runtime_image": "ghcr.io/newtontech/nwchem:7.2.0"}
    )
    assert assumption["software_version"] == "7.2.0"
    assert assumption["exact_runtime_known"] is True
    assert assumption["declared_by"] == "intent"


# --------------------------------------------------------------------------- #
# Fixture regression expectations                                             #
# --------------------------------------------------------------------------- #


def _codes(diagnostics: list[dict]) -> set[str]:
    return {item["code"] for item in diagnostics}


def _fixture(case: str) -> Path:
    return FIXTURES / case / "input.nw"


def test_fixture_valid_dft_is_clean_apart_from_version_note() -> None:
    diagnostics, _ = preflight_diagnostics(_fixture("valid_dft"))
    blocking = [item for item in diagnostics if item["blocking"]]
    assert blocking == []
    assert CODE_MISSING_BLOCK not in _codes(diagnostics)
    assert CODE_STRUCTURE_EMPTY not in _codes(diagnostics)
    assert CODE_MISSING_BASIS not in _codes(diagnostics)
    # Without the intent contract loaded, the version-assumption info note is
    # the only emission. The tool layer (check_path) loads the intent and
    # suppresses it; that path is exercised below.
    assert CODE_VERSION_ASSUMPTION in _codes(diagnostics)


def test_fixture_valid_dft_via_tool_suppresses_version_note_with_intent() -> None:
    payload = preflight_path(FIXTURES / "valid_dft")
    codes = {item["code"] for item in payload["diagnostics"]}
    # The valid_dft fixture ships an intent.json declaring software_version, so
    # the version-assumption information note is suppressed and the case is ok.
    assert CODE_VERSION_ASSUMPTION not in codes
    assert payload["ok"] is True
    assert payload["diagnostic_envelope"] == "v1"


def test_fixture_missing_required_blocks() -> None:
    diagnostics, graph = preflight_diagnostics(_fixture("missing_required"))
    assert CODE_MISSING_BLOCK in _codes(diagnostics)
    missing = [item for item in diagnostics if item["code"] == CODE_MISSING_BLOCK]
    assert any(item["blocking"] for item in missing)
    # Every diagnostic must carry the full envelope field set the issue requires.
    for item in missing:
        assert item["category"] == "cross-file reference"
        assert "source_provenance" in item
        assert "fix_hints" in item
        assert "actions" in item
        assert "range" in item
        assert "artifact_roles" in item
    # The graph records the structure/task roles as missing.
    structure_nodes = graph.by_role("structure")
    assert any(not node.exists for node in structure_nodes)
    task_nodes = graph.by_role("task")
    assert any(not node.exists for node in task_nodes)


def test_fixture_task_without_section() -> None:
    diagnostics, _ = preflight_diagnostics(_fixture("task_without_section"))
    assert CODE_TASK_WITHOUT_SECTION in _codes(diagnostics)
    item = next(d for d in diagnostics if d["code"] == CODE_TASK_WITHOUT_SECTION)
    assert item["severity"] == "error"
    assert item["blocking"] is True
    assert item["source_provenance"]["task_theory"] == "dft"


def test_fixture_theory_basis_mismatch() -> None:
    diagnostics, _ = preflight_diagnostics(_fixture("theory_basis_mismatch"))
    assert CODE_THEORY_BASIS_MISMATCH in _codes(diagnostics)
    item = next(d for d in diagnostics if d["code"] == CODE_THEORY_BASIS_MISMATCH)
    assert item["severity"] == "error"
    assert item["blocking"] is True
    assert item["source_provenance"]["task_theory"] == "mp2"
    assert item["source_provenance"]["basis_library"] == "sto-3g"
    assert "version_assumption" in item


def test_fixture_ecp_minimal_basis() -> None:
    diagnostics, _ = preflight_diagnostics(_fixture("ecp_minimal_basis"))
    assert CODE_ECP_WITHOUT_BASIS in _codes(diagnostics)
    item = next(d for d in diagnostics if d["code"] == CODE_ECP_WITHOUT_BASIS)
    assert item["severity"] == "warning"
    assert item["blocking"] is False


def test_fixture_low_memory_warning() -> None:
    diagnostics, _ = preflight_diagnostics(_fixture("low_memory"))
    assert CODE_LOW_MEMORY in _codes(diagnostics)
    item = next(d for d in diagnostics if d["code"] == CODE_LOW_MEMORY)
    assert item["severity"] == "warning"
    assert item["blocking"] is False
    assert item["source_provenance"]["threshold_source"] == "default"
    assert item["facts"]["memory_mb"] < DEFAULT_MEMORY_WARNING_MB


# --------------------------------------------------------------------------- #
# Diagnostic field completeness (acceptance criteria)                        #
# --------------------------------------------------------------------------- #


def test_every_preflight_diagnostic_carries_required_envelope_fields() -> None:
    diagnostics, _ = preflight_diagnostics(_fixture("missing_required"))
    diagnostics_low, _ = preflight_diagnostics(_fixture("low_memory"))
    diagnostics_tbm, _ = preflight_diagnostics(_fixture("theory_basis_mismatch"))
    for item in diagnostics + diagnostics_low + diagnostics_tbm:
        for field in (
            "code",
            "severity",
            "path",
            "range",
            "blocking",
            "category",
            "source_provenance",
            "fix_hints",
            "confidence",
            "source",
        ):
            assert field in item, f"{item['code']} missing {field}"
        # fix_hints OR actions must be present (issue acceptance criterion).
        assert item["fix_hints"] or item.get("actions")
        assert "start" in item["range"] and "end" in item["range"]


def test_dft_without_functional_emits_version_aware_diagnostic() -> None:
    nw = (
        "geometry\n  O 0 0 0\nend\n"
        "basis\n  O library 6-31g\nend\n"
        "dft\n  mult 1\nend\n"
        "task dft\n"
    )
    path = FIXTURES.parent / "_tmp_dft_no_xc.nw"
    path.write_text(nw, encoding="utf-8")
    try:
        diagnostics, _ = preflight_diagnostics(path)
        assert CODE_DFT_WITHOUT_FUNCTIONAL in _codes(diagnostics)
        item = next(d for d in diagnostics if d["code"] == CODE_DFT_WITHOUT_FUNCTIONAL)
        assert "version_assumption" in item
        assert "schema_source" in item["source_provenance"]
    finally:
        path.unlink()


def test_task_dft_without_basis_emits_task_basis_mismatch() -> None:
    nw = "geometry\n  O 0 0 0\nend\ntask dft\n"
    path = FIXTURES.parent / "_tmp_task_dft_no_basis.nw"
    path.write_text(nw, encoding="utf-8")
    try:
        diagnostics, _ = preflight_diagnostics(path)
        # task dft + no basis block -> task/basis mismatch warning fires.
        assert CODE_TASK_BASIS_MISMATCH in _codes(diagnostics)
    finally:
        path.unlink()


def test_intent_overrides_memory_threshold() -> None:
    diagnostics, _ = preflight_diagnostics(
        _fixture("low_memory"),
        intent={"memory_warning_mb": 32.0},
    )
    low = [d for d in diagnostics if d["code"] == CODE_LOW_MEMORY]
    # 64 mb >= 32 mb threshold -> the warning is suppressed.
    assert low == []


def test_intent_declared_version_suppresses_version_note() -> None:
    diagnostics, _ = preflight_diagnostics(
        _fixture("valid_dft"),
        intent={"software_version": "7.2.0"},
    )
    assert CODE_VERSION_ASSUMPTION not in _codes(diagnostics)


# --------------------------------------------------------------------------- #
# Agent CLI wiring                                                            #
# --------------------------------------------------------------------------- #


def test_check_path_returns_envelope_payload() -> None:
    payload = check_path(_fixture("missing_required"))
    assert payload["software"] == SOFTWARE
    assert payload["diagnostic_envelope"] == "v1"
    assert payload["ok"] is False  # missing blocks are blocking.
    codes = {item["code"] for item in payload["diagnostics"]}
    assert CODE_MISSING_BLOCK in codes


def test_preflight_path_returns_graph_artifacts() -> None:
    payload = preflight_path(FIXTURES / "task_without_section")
    assert payload["operation"] == "preflight"
    assert payload["diagnostic_envelope"] == "v1"
    assert isinstance(payload.get("artifacts"), list)
    roles = {node["role"] for node in payload["artifacts"]}
    assert "structure" in roles
    assert "task" in roles
    assert CODE_TASK_WITHOUT_SECTION in {item["code"] for item in payload["diagnostics"]}


def test_manifest_path_merges_fixture_expectations() -> None:
    manifest = manifest_path(FIXTURES / "valid_dft")
    fixtures = manifest["capabilities"]["fleet-regression-fixtures"]["fixtures"]
    names = {item["name"] for item in fixtures}
    assert "valid_dft" in names
    assert "missing_required" in names


def test_manifest_path_without_case_dir_returns_canonical_manifest() -> None:
    manifest = manifest_path(None)
    assert manifest["software"] == SOFTWARE
    assert manifest["preflight_envelope"] == "DiagnosticEnvelope/v1"
    # No fixtures merged in when no case directory is supplied.
    assert manifest["capabilities"]["fleet-regression-fixtures"]["fixtures"] == []


def test_looks_like_nwchem_workspace_detects_nw_file() -> None:
    assert looks_like_nwchem_workspace(_fixture("valid_dft")) is True


def test_looks_like_nwchem_workspace_detects_case_dir() -> None:
    assert looks_like_nwchem_workspace(FIXTURES / "valid_dft") is True


def test_looks_like_nwchem_workspace_rejects_unrelated_file(tmp_path: Path) -> None:
    other = tmp_path / "notes.txt"
    other.write_text("just some prose", encoding="utf-8")
    assert looks_like_nwchem_workspace(other) is False


# --------------------------------------------------------------------------- #
# CLI entrypoint (subprocess-free, via tool.main)                             #
# --------------------------------------------------------------------------- #


def _run_tool(argv: list[str]) -> tuple[int, dict]:
    from nwchem_lsp.tool import main

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(argv)
    return rc, json.loads(buf.getvalue())


def test_cli_manifest_emits_machine_readable_manifest() -> None:
    rc, payload = _run_tool(["manifest", str(FIXTURES / "valid_dft")])
    assert rc == 0
    assert payload["software"] == SOFTWARE
    assert payload["preflight_envelope"] == "DiagnosticEnvelope/v1"


def test_cli_preflight_fail_on_blocking_returns_nonzero() -> None:
    rc, _payload = _run_tool(
        ["preflight", str(FIXTURES / "missing_required"), "--fail-on-blocking"]
    )
    assert rc == 1


def test_cli_check_fail_on_blocking_clean_fixture_returns_zero() -> None:
    rc, _payload = _run_tool(
        ["check", str(_fixture("valid_dft")), "--fail-on-blocking"]
    )
    assert rc == 0

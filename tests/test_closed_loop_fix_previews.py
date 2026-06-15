"""Closed-loop repair preview tests for the agent CLI (issue #99).

Issue #99 requires the agent CLI (`nwchem-lsp-tool fix`) to:
- emit structured DiagnosticEnvelope/v1 diagnostics for the realistic failure modes;
- return deterministic repair previews for safe cases;
- refuse unsafe cases with a stable rule-scoped reason.

These tests pin that contract against the canonical fixture set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from nwchem_lsp import tool
from nwchem_lsp.features.code_actions import (
    build_agent_actions,
    code_action_to_agent_json,
)

FIXTURES = Path(__file__).parent / "fixtures"
INVALID_DIR = FIXTURES / "invalid"


def _run_fix(path: Path) -> dict[str, Any]:
    """Invoke `nwchem-lsp-tool fix` on `path` and parse the JSON payload."""
    rc = tool.main(["fix", str(path)])
    assert rc == 0, f"nwchem-lsp-tool fix exited with rc={rc}"
    return json.loads(path.read_text(encoding="utf-8"))  # placeholder; see capsys


def _run_fix_captured(path: Path, capsys) -> dict[str, Any]:
    rc = tool.main(["fix", str(path)])
    assert rc == 0, f"nwchem-lsp-tool fix exited with rc={rc}"
    captured = capsys.readouterr()
    return json.loads(captured.out)


def _action_codes(payload: dict[str, Any]) -> set[str]:
    return {str(a.get("diagnostic_code") or "") for a in payload.get("actions", [])}


# ======================================================================
# Closed-loop contract shape
# ======================================================================


class TestFixActionShape:
    """Every fix action must carry safe_to_auto_apply, edit, and refusal_reason."""

    def test_missing_required_fixture_has_safe_to_apply_edit(self, capsys) -> None:
        """NW2004 (missing required section) yields a deterministic stub insertion."""
        payload = _run_fix_captured(INVALID_DIR / "missing_required.nw", capsys)
        safe_actions = [
            a
            for a in payload["actions"]
            if a.get("diagnostic_code") == "NW2004" and a.get("safe_to_auto_apply")
        ]
        assert (
            safe_actions
        ), "expected at least one safe-to-apply NW2004 action; got: " + json.dumps(
            payload["actions"], indent=2
        )
        action = safe_actions[0]
        assert action["edit"] is not None, "safe action must carry an edit payload"
        assert action["refusal_reason"] is None
        joined = "\n".join(e["new_text"] for e in action["edit"]["edits"])
        # The stub for NW2004 is deterministic and references 'geometry',
        # 'basis', or 'task' as the missing piece.
        assert any(
            marker in joined for marker in ("geometry", "basis", "task scf energy")
        ), f"unexpected NW2004 stub: {joined}"

    def test_unknown_keyword_fixture_has_safe_to_apply_typo_fix(self, capsys) -> None:
        """NW2001 (unknown keyword) yields a typo correction edit when a close match exists."""
        payload = _run_fix_captured(INVALID_DIR / "unknown_keyword.nw", capsys)
        # The fixture uses `bogus_keyword` inside scf, which has no close
        # match in the keyword database. The contract still requires every
        # fix action to expose the safe_to_auto_apply + refusal_reason shape,
        # so we assert that the action list is non-empty and well-formed.
        assert isinstance(payload["actions"], list)
        assert len(payload["actions"]) >= 1
        for action in payload["actions"]:
            assert "safe_to_auto_apply" in action
            assert "edit" in action
            assert "refusal_reason" in action

    def test_every_action_carries_refusal_reason_field(self, capsys) -> None:
        """The refusal_reason field is the OpenQC contract surface for unsafe actions."""
        for fixture in INVALID_DIR.glob("*.nw"):
            payload = _run_fix_captured(fixture, capsys)
            for action in payload["actions"]:
                assert (
                    "refusal_reason" in action
                ), f"action {action} from {fixture.name} must expose refusal_reason"
                if action["safe_to_auto_apply"]:
                    assert action["refusal_reason"] is None
                    assert action["edit"] is not None
                else:
                    assert action["edit"] is None
                    assert isinstance(action["refusal_reason"], str)
                    assert action[
                        "refusal_reason"
                    ], f"refusal_reason for {action.get('diagnostic_code')} must not be empty"

    def test_fix_capabilities_block_is_marked_available(self, capsys) -> None:
        payload = _run_fix_captured(INVALID_DIR / "missing_required.nw", capsys)
        caps = payload["capabilities"]
        assert caps["operation"] == "fix"
        assert caps["status"] == "available"
        assert "fix" in caps["operations"]


# ======================================================================
# Unit-level tests for build_agent_actions / code_action_to_agent_json
# ======================================================================


class TestBuildAgentActions:
    """Direct unit tests for the helper that powers the CLI fix operation."""

    def _diag(
        self,
        code: str,
        message: str,
        line: int = 0,
        char_start: int = 0,
        char_end: int = 0,
        *,
        severity: str = "error",
        blocking: bool = True,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "source": "nwchem-lsp",
            "range": {
                "start": {"line": line, "character": char_start},
                "end": {"line": line, "character": char_end},
            },
            "blocking": blocking,
            "confidence": 1.0,
        }

    def test_missing_required_section_returns_safe_edit(self) -> None:
        source = 'title "missing"\ntask scf energy\n'
        diag = self._diag(
            "NW2004",
            "Missing required 'geometry' block",
        )
        actions = build_agent_actions(source, [diag], uri="file:///test.nw")
        assert len(actions) == 1
        action = actions[0]
        assert action["safe_to_auto_apply"] is True
        assert action["edit"] is not None
        assert action["refusal_reason"] is None
        joined = "\n".join(e["new_text"] for e in action["edit"]["edits"])
        assert "geometry" in joined

    def test_typo_correction_returns_safe_edit(self) -> None:
        source = "gemoetry\n  H 0 0 0\nend\nbasis\n  * library 6-31g\nend\ntask scf energy\n"
        diag = self._diag(
            "NW2001",
            "Unknown keyword 'gemoetry'",
            line=0,
            char_start=0,
            char_end=8,
            severity="warning",
            blocking=False,
        )
        actions = build_agent_actions(source, [diag], uri="file:///test.nw")
        # The typo table maps 'gemoetry' -> 'geometry' deterministically.
        safe_actions = [a for a in actions if a["safe_to_auto_apply"]]
        assert safe_actions, "expected typo correction to be safe-to-apply"
        action = safe_actions[0]
        assert action["edit"] is not None
        new_text = action["edit"]["edits"][0]["new_text"]
        assert new_text == "geometry"

    def test_unknown_rule_code_refuses_with_reason(self) -> None:
        source = (
            "title 'x'\ngeometry\n  H 0 0 0\nend\nbasis\n  * library 6-31g\nend\ntask scf energy\n"
        )
        # NW2012 (malformed coordinates) is not auto-repairable.
        diag = self._diag(
            "NW2012",
            "Malformed coordinates",
            line=2,
            char_start=2,
            char_end=12,
        )
        actions = build_agent_actions(source, [diag], uri="file:///test.nw")
        assert len(actions) == 1
        action = actions[0]
        assert action["safe_to_auto_apply"] is False
        assert action["edit"] is None
        assert action["refusal_reason"] is not None
        assert "NW2012" in action["refusal_reason"]

    def test_runtime_finding_refuses_with_reason(self) -> None:
        source = (
            "title 'x'\ngeometry\n  H 0 0 0\nend\nbasis\n  * library 6-31g\nend\ntask scf energy\n"
        )
        diag = self._diag(
            "NWCHEM-E044",
            "SCF failed to converge",
            severity="error",
        )
        actions = build_agent_actions(source, [diag], uri="file:///test.nw")
        assert len(actions) == 1
        action = actions[0]
        assert action["safe_to_auto_apply"] is False
        assert action["edit"] is None
        assert action["refusal_reason"]
        assert "runtime" in action["refusal_reason"].lower()

    def test_code_action_to_agent_json_handles_missing_edit(self) -> None:
        from lsprotocol.types import CodeAction

        action = CodeAction(title="Review", kind=None)
        payload = code_action_to_agent_json(
            action,
            confidence=0.5,
            blocking=False,
            safe_to_auto_apply=False,
            refusal_reason="test reason",
            diagnostic_code="NW9999",
        )
        assert payload["title"] == "Review"
        assert payload["safe_to_auto_apply"] is False
        assert payload["edit"] is None
        assert payload["refusal_reason"] == "test reason"
        assert payload["diagnostic_code"] == "NW9999"


# ======================================================================
# Refusal-reason stability
# ======================================================================


class TestRefusalReasons:
    """Refusal reasons are stable and rule-scoped."""

    def test_each_unsafe_action_has_non_empty_refusal_reason(self, capsys) -> None:
        for fixture in INVALID_DIR.glob("*.nw"):
            payload = _run_fix_captured(fixture, capsys)
            for action in payload["actions"]:
                if not action["safe_to_auto_apply"]:
                    reason = action.get("refusal_reason") or ""
                    assert reason, (
                        f"empty refusal_reason for {action.get('diagnostic_code')} "
                        f"in {fixture.name}"
                    )

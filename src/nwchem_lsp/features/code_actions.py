"""Code actions provider for NWChem LSP.

Provides quick fixes for common NWChem input file errors, routed through
stable diagnostic rule codes (NWxxxx) produced by the lint subsystem.

Supported rule codes
--------------------
NW1001  Unclosed section -> add ``end``
NW1002  Unexpected ``end`` -> remove stray ``end``
NW2001  Unknown keyword in section -> casing / typo correction
NW2002  Invalid enum value -> suggest closest valid value
NW2004  Missing required section -> insert section stub
NW2005  Unknown task theory -> correct to nearest valid theory
NW2006  Unknown task operation -> correct to nearest valid operation
NW2007  Unknown basis set -> suggest closest known basis set
NW2008  Unknown DFT functional -> suggest closest known functional
NW2009  Unknown top-level directive -> casing / typo correction
NW2010  Duplicate section -> remove the duplicate block
"""

from __future__ import annotations

import re
from typing import Any, Optional

from lsprotocol.types import (
    CodeAction,
    CodeActionKind,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)

from ..data.keywords import (
    BASIS_SETS,
    DFT_FUNCTIONALS,
    TASK_OPERATIONS,
    TASK_THEORIES,
    TOP_LEVEL_SECTIONS,
    get_all_keyword_names,
)
from ..parser.nwchem_parser import NwchemParser

# Lowercase lookup sets for fast membership checks
_BASIS_SETS_LOWER: set[str] = {b.lower() for b in BASIS_SETS}
_FUNCTIONALS_LOWER: set[str] = {f.lower() for f in DFT_FUNCTIONALS}
_TASK_THEORIES_LOWER: set[str] = {t.lower() for t in TASK_THEORIES}
_TASK_OPERATIONS_LOWER: set[str] = {o.lower() for o in TASK_OPERATIONS}
_TOP_LEVEL_LOWER: set[str] = {s.lower() for s in TOP_LEVEL_SECTIONS} | {
    k.lower()
    for k in (
        "start",
        "restart",
        "title",
        "echo",
        "set",
        "unset",
        "stop",
        "task",
        "charge",
        "memory",
        "permanent_dir",
        "scratch_dir",
        "print",
    )
}


def _extract_quoted(message: str) -> str:
    """Extract the first single-quoted token from *message*."""
    parts = message.split("'")
    if len(parts) >= 2:
        return parts[1]
    return ""


def _edit_single(uri: str, line: int, col_start: int, col_end: int, new_text: str) -> WorkspaceEdit:
    """Build a WorkspaceEdit that replaces a single range."""
    return WorkspaceEdit(
        changes={
            uri: [
                TextEdit(
                    range=Range(
                        start=Position(line=line, character=col_start),
                        end=Position(line=line, character=col_end),
                    ),
                    new_text=new_text,
                )
            ]
        }
    )


def _closest(target: str, candidates: set[str], threshold: float = 0.6) -> Optional[str]:
    """Return the closest string match above *threshold* using normalised edit distance."""
    if len(target) < 2:
        return None

    best: Optional[str] = None
    best_score = 0.0

    for cand in candidates:
        score = _similarity(target, cand)
        if score > best_score and score >= threshold:
            best_score = score
            best = cand

    return best


def _similarity(s1: str, s2: str) -> float:
    """Normalised Levenshtein similarity (0-1)."""
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    if not s2:
        return 1.0 if not s1 else 0.0

    previous = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current = [i + 1]
        for j, c2 in enumerate(s2):
            current.append(
                min(
                    previous[j + 1] + 1,
                    current[j] + 1,
                    previous[j] + (c1 != c2),
                )
            )
        previous = current

    return 1.0 - previous[-1] / max(len(s1), len(s2))


class CodeActionsProvider:
    """Provides code actions (quick fixes) for NWChem input files."""

    def __init__(self) -> None:
        """Initialize code actions provider."""
        self.valid_keywords = set(get_all_keyword_names())
        self.section_keywords = NwchemParser.SECTION_KEYWORDS

        # Common typo table for deterministic correction before fuzzy matching
        self._typos: dict[str, str] = {
            "gemoetry": "geometry",
            "gemetry": "geometry",
            "goemetry": "geometry",
            "geometery": "geometry",
            "geometri": "geometry",
            "basiss": "basis",
            "bassis": "basis",
            "basas": "basis",
            "basi": "basis",
            "taks": "task",
            "tsk": "task",
            "titile": "title",
            "titlle": "title",
            "sart": "start",
            "strat": "start",
            "endd": "end",
            "ned": "end",
            "sfc": "scf",
            "dfs": "dft",
            "dfft": "dft",
            "pritn": "print",
            "prin": "print",
            "echoo": "echo",
            "ecko": "echo",
            "optimise": "optimize",
            "optimiz": "optimize",
            "optmize": "optimize",
            "energie": "energy",
            "enrgy": "energy",
            "frequecy": "frequencies",
            "freq": "frequencies",
            "theorry": "theory",
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def get_code_actions(
        self,
        source: str,
        diagnostics: list[Diagnostic],
        uri: str = "document",
    ) -> list[CodeAction]:
        """Get code actions for the given diagnostics.

        Args:
            source: Full document text.
            diagnostics: Diagnostics published for the document.
            uri: Document URI used inside WorkspaceEdit changes.

        Returns:
            List of CodeAction objects.
        """
        actions: list[CodeAction] = []

        for diagnostic in diagnostics:
            action = self._action_for_diagnostic(source, diagnostic, uri)
            if action is not None:
                actions.append(action)

        actions.extend(self._general_actions(source, uri))
        return actions

    # ------------------------------------------------------------------
    # Dispatch by rule code
    # ------------------------------------------------------------------

    def _action_for_diagnostic(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Dispatch a single diagnostic to the appropriate fix handler."""
        code = str(diag.code) if diag.code else ""

        # Map rule code to handler
        handler = {
            "NW1001": self._fix_unclosed_section,
            "NW1002": self._fix_unexpected_end,
            "NW2001": self._fix_unknown_keyword,
            "NW2002": self._fix_invalid_enum,
            "NW2004": self._fix_missing_section,
            "NW2005": self._fix_unknown_task_theory,
            "NW2006": self._fix_unknown_task_operation,
            "NW2007": self._fix_unknown_basis_set,
            "NW2008": self._fix_unknown_functional,
            "NW2009": self._fix_unknown_directive,
            "NW2010": self._fix_duplicate_section,
        }.get(code)

        if handler is not None:
            return handler(source, diag, uri)

        # Fallback: match on message text for diagnostics without a rule code
        return self._fallback_by_message(source, diag, uri)

    # ------------------------------------------------------------------
    # NW1xxx -- Syntax fixes
    # ------------------------------------------------------------------

    def _fix_unclosed_section(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> CodeAction:
        """Add 'end' to close an unclosed section (NW1001)."""
        lines = source.split("\n")
        line_num = diag.range.start.line

        section_name = _extract_quoted(diag.message) or "section"

        # Insert 'end' after the last non-empty line of the section
        insert_line = line_num + 1
        while insert_line < len(lines) and lines[insert_line].strip():
            insert_line += 1

        if insert_line >= len(lines):
            insert_pos = Position(line=len(lines) - 1, character=len(lines[-1]))
            new_text = "\nend"
        else:
            insert_pos = Position(line=insert_line, character=0)
            new_text = "end\n"

        return CodeAction(
            title=f"Add 'end' to close '{section_name}' section",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=WorkspaceEdit(
                changes={
                    uri: [
                        TextEdit(
                            range=Range(start=insert_pos, end=insert_pos),
                            new_text=new_text,
                        )
                    ]
                }
            ),
        )

    def _fix_unexpected_end(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Remove a stray 'end' (NW1002)."""
        line_num = diag.range.start.line
        lines = source.split("\n")

        if line_num < len(lines) and lines[line_num].strip().lower() == "end":
            start_pos = Position(line=line_num, character=0)
            end_pos = (
                Position(line=line_num + 1, character=0)
                if line_num + 1 < len(lines)
                else Position(line=line_num, character=len(lines[line_num]))
            )
            return CodeAction(
                title="Remove unexpected 'end' keyword",
                kind=CodeActionKind.QuickFix,
                diagnostics=[diag],
                edit=WorkspaceEdit(
                    changes={
                        uri: [
                            TextEdit(
                                range=Range(start=start_pos, end=end_pos),
                                new_text="",
                            )
                        ]
                    }
                ),
            )
        return None

    # ------------------------------------------------------------------
    # NW2xxx -- Schema fixes
    # ------------------------------------------------------------------

    def _fix_unknown_keyword(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Correct a misspelled / wrongly-cased keyword (NW2001)."""
        unknown_kw = _extract_quoted(diag.message).lower()
        if not unknown_kw:
            return None

        suggestion = self._find_closest_keyword(unknown_kw)
        if not suggestion:
            return None

        line = diag.range.start.line
        col_start = diag.range.start.character
        col_end = col_start + len(unknown_kw)

        return CodeAction(
            title=f"Replace '{unknown_kw}' with '{suggestion}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=_edit_single(uri, line, col_start, col_end, suggestion),
        )

    def _fix_invalid_enum(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Suggest the closest valid value for an enum violation (NW2002)."""
        value = _extract_quoted(diag.message).lower()
        if not value:
            return None

        # Determine which enum set from message content
        msg_lower = diag.message.lower()
        candidates: set[str] = set()

        if "units" in msg_lower:
            candidates = {"angstroms", "bohr", "nanometers", "picometers", "au"}
        elif "grid" in msg_lower:
            candidates = {"coarse", "medium", "fine", "xfine", "ultrafine"}

        if not candidates:
            return None

        suggestion = _closest(value, candidates)
        if not suggestion:
            return None

        line = diag.range.start.line
        col_start = diag.range.start.character
        col_end = col_start + len(value)

        return CodeAction(
            title=f"Replace '{value}' with '{suggestion}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=_edit_single(uri, line, col_start, col_end, suggestion),
        )

    def _fix_missing_section(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Insert a stub for a missing required section (NW2004)."""
        msg_lower = diag.message.lower()

        if "'geometry'" in msg_lower:
            stub = "\ngeometry\n  H 0 0 0\nend\n"
            title = "Add 'geometry' section stub"
        elif "'basis'" in msg_lower:
            stub = "\nbasis\n  * library 6-31G*\nend\n"
            title = "Add 'basis' section stub"
        elif "'task'" in msg_lower:
            stub = "\ntask scf energy\n"
            title = "Add 'task' directive stub"
        else:
            return None

        # Append at end of file
        lines = source.split("\n")
        insert_pos = Position(line=len(lines) - 1, character=len(lines[-1]))

        return CodeAction(
            title=title,
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=WorkspaceEdit(
                changes={
                    uri: [
                        TextEdit(
                            range=Range(start=insert_pos, end=insert_pos),
                            new_text=stub,
                        )
                    ]
                }
            ),
        )

    def _fix_unknown_task_theory(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Correct a misspelled task theory (NW2005)."""
        value = _extract_quoted(diag.message).lower()
        if not value:
            return None

        suggestion = _closest(value, _TASK_THEORIES_LOWER)
        if not suggestion:
            return None

        line = diag.range.start.line
        col_start = diag.range.start.character
        col_end = col_start + len(value)

        return CodeAction(
            title=f"Replace task theory '{value}' with '{suggestion}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=_edit_single(uri, line, col_start, col_end, suggestion),
        )

    def _fix_unknown_task_operation(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Correct a misspelled task operation (NW2006)."""
        value = _extract_quoted(diag.message).lower()
        if not value:
            return None

        suggestion = _closest(value, _TASK_OPERATIONS_LOWER)
        if not suggestion:
            return None

        line = diag.range.start.line
        col_start = diag.range.start.character
        col_end = col_start + len(value)

        return CodeAction(
            title=f"Replace task operation '{value}' with '{suggestion}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=_edit_single(uri, line, col_start, col_end, suggestion),
        )

    def _fix_unknown_basis_set(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Suggest the closest known basis set (NW2007)."""
        value = _extract_quoted(diag.message).lower()
        if not value:
            return None

        suggestion = _closest(value, _BASIS_SETS_LOWER)
        if not suggestion:
            return None

        # Use the canonical casing from BASIS_SETS
        canonical = next((b for b in BASIS_SETS if b.lower() == suggestion), suggestion)

        line = diag.range.start.line
        col_start = diag.range.start.character
        col_end = col_start + len(value)

        return CodeAction(
            title=f"Replace basis set '{value}' with '{canonical}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=_edit_single(uri, line, col_start, col_end, canonical),
        )

    def _fix_unknown_functional(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Suggest the closest known DFT functional (NW2008)."""
        value = _extract_quoted(diag.message).lower()
        if not value:
            return None

        suggestion = _closest(value, _FUNCTIONALS_LOWER)
        if not suggestion:
            return None

        # Use the canonical casing from DFT_FUNCTIONALS
        canonical = next((f for f in DFT_FUNCTIONALS if f.lower() == suggestion), suggestion)

        line = diag.range.start.line
        col_start = diag.range.start.character
        col_end = col_start + len(value)

        return CodeAction(
            title=f"Replace functional '{value}' with '{canonical}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=_edit_single(uri, line, col_start, col_end, canonical),
        )

    def _fix_unknown_directive(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Correct an unknown top-level directive (NW2009)."""
        value = _extract_quoted(diag.message).lower()
        if not value:
            return None

        suggestion = self._find_closest_keyword(value)
        if not suggestion:
            suggestion = _closest(value, _TOP_LEVEL_LOWER)
        if not suggestion:
            return None

        line = diag.range.start.line
        col_start = diag.range.start.character
        col_end = col_start + len(value)

        return CodeAction(
            title=f"Replace '{value}' with '{suggestion}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=_edit_single(uri, line, col_start, col_end, suggestion),
        )

    def _fix_duplicate_section(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Remove a duplicate section block (NW2010)."""
        line_num = diag.range.start.line
        lines = source.split("\n")

        if line_num >= len(lines):
            return None

        # Find the section start line (the diagnostic points at it)
        start_line = line_num

        # Find the matching 'end' for this section
        end_line = start_line
        depth = 0
        for i in range(start_line, len(lines)):
            stripped = lines[i].strip().lower()
            parts = stripped.split()
            if parts and parts[0] in self.section_keywords:
                depth += 1
            elif stripped == "end":
                depth -= 1
                if depth <= 0:
                    end_line = i
                    break
        else:
            # No matching end -- delete to the end of the file or next section
            end_line = len(lines) - 1

        # Remove from start_line through end_line (inclusive)
        del_start = Position(line=start_line, character=0)
        del_end = (
            Position(line=end_line + 1, character=0)
            if end_line + 1 < len(lines)
            else Position(line=end_line, character=len(lines[end_line]))
        )

        return CodeAction(
            title="Remove duplicate section",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diag],
            edit=WorkspaceEdit(
                changes={
                    uri: [
                        TextEdit(
                            range=Range(start=del_start, end=del_end),
                            new_text="",
                        )
                    ]
                }
            ),
        )

    # ------------------------------------------------------------------
    # Fallback: message-based matching (no rule code)
    # ------------------------------------------------------------------

    def _fallback_by_message(
        self,
        source: str,
        diag: Diagnostic,
        uri: str,
    ) -> Optional[CodeAction]:
        """Handle diagnostics that lack a stable rule code."""
        msg = diag.message.lower()

        if "unclosed section" in msg:
            return self._fix_unclosed_section(source, diag, uri)
        if "unexpected 'end'" in msg:
            return self._fix_unexpected_end(source, diag, uri)
        if "unknown keyword" in msg:
            return self._fix_unknown_keyword(source, diag, uri)

        return None

    # ------------------------------------------------------------------
    # General (non-diagnostic) actions
    # ------------------------------------------------------------------

    def _general_actions(self, source: str, uri: str) -> list[CodeAction]:
        """General code actions not tied to specific diagnostics."""
        actions: list[CodeAction] = []

        start_action = self._create_add_start_action(source, uri)
        if start_action is not None:
            actions.append(start_action)

        return actions

    def _create_add_start_action(self, source: str, uri: str) -> Optional[CodeAction]:
        """Create an action to add a missing 'start' directive."""
        for line in source.split("\n"):
            stripped = line.strip().lower()
            if stripped.startswith("start ") or stripped == "start":
                return None

        return CodeAction(
            title="Add missing 'start' directive",
            kind=CodeActionKind.QuickFix,
            edit=WorkspaceEdit(
                changes={
                    uri: [
                        TextEdit(
                            range=Range(
                                start=Position(line=0, character=0),
                                end=Position(line=0, character=0),
                            ),
                            new_text="start molecule\n\n",
                        )
                    ]
                }
            ),
        )

    # ------------------------------------------------------------------
    # Keyword matching helpers
    # ------------------------------------------------------------------

    def _find_closest_keyword(self, unknown: str) -> Optional[str]:
        """Find the closest matching valid keyword."""
        if len(unknown) < 2:
            return None

        # Exact typo table first (deterministic, no false positives)
        if unknown in self._typos:
            return self._typos[unknown]

        # Fuzzy match against all known keywords
        return _closest(unknown, self.valid_keywords, threshold=0.6)

    # Keep the old public spelling for backward-compat with tests
    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity score between two strings (0-1)."""
        return _similarity(s1, s2)


# ======================================================================
# Agent CLI integration (closed-loop repair previews)
# ======================================================================
#
# The block below wires the LSP-side CodeActionsProvider into the agent CLI
# (`nwchem-lsp-tool fix`). The CLI sees diagnostics as plain dicts and needs
# the same deterministic edit previews the editor shows in code-action
# tooltips, so we provide:
# - :meth:`CodeActionsProvider.build_agent_actions` -- one entry point that
#   turns a source string + diagnostics-as-dicts into the JSON action list
#   the agent CLI returns. Each action carries `safe_to_auto_apply`,
#   `edit.edits`, and a stable `refusal_reason` so agents can decide which
#   preview to apply without re-running the LSP.
# - :func:`code_action_to_agent_json` -- pure helper that converts an LSP
#   CodeAction/WorkspaceEdit object into the JSON dict shape.Kept at module
#   scope so tests can call it directly.


def _position_to_json(pos: Position) -> dict[str, int]:
    return {"line": int(pos.line), "character": int(pos.character)}


def _range_to_json(range_: Range) -> dict[str, dict[str, int]]:
    return {
        "start": _position_to_json(range_.start),
        "end": _position_to_json(range_.end),
    }


def _text_edit_to_json(edit: TextEdit) -> dict[str, Any]:
    return {
        "range": _range_to_json(edit.range),
        "new_text": edit.new_text,
    }


def _workspace_edit_to_json(
    edit: Optional[WorkspaceEdit],
) -> Optional[dict[str, list[dict[str, Any]]]]:
    """Convert an LSP WorkspaceEdit to the JSON changes shape.

    Returns ``{"edits": [...]}`` where every edit carries its absolute
    ``range`` (line/character are 0-based) and ``new_text``. The shape
    mirrors the cif-lsp agent CLI so OpenQC can consume both LSPs with the
    same parser.
    """
    if edit is None or not edit.changes:
        return None
    edits: list[dict[str, Any]] = []
    # Iterate in insertion order; the agent CLI does not depend on the URI
    # key because all edits are anchored to the same input file.
    for changes in edit.changes.values():
        for change in changes:
            edits.append(_text_edit_to_json(change))
    if not edits:
        return None
    return {"edits": edits}


def code_action_to_agent_json(
    action: CodeAction,
    *,
    confidence: float = 1.0,
    blocking: bool = False,
    safe_to_auto_apply: bool = True,
    refusal_reason: Optional[str] = None,
    diagnostic_code: Optional[str] = None,
    diagnostic_range: Optional[Range] = None,
) -> dict[str, Any]:
    """Convert an LSP CodeAction to the agent CLI JSON shape."""
    payload: dict[str, Any] = {
        "title": action.title,
        "kind": str(action.kind) if action.kind is not None else "quickfix",
        "diagnostic_code": diagnostic_code,
        "diagnostic_range": (
            _range_to_json(diagnostic_range) if diagnostic_range is not None else None
        ),
        "confidence": confidence,
        "blocking": blocking,
        "safe_to_auto_apply": safe_to_auto_apply,
        "edit": _workspace_edit_to_json(action.edit),
        "refusal_reason": refusal_reason,
        "data": {"source": "nwchem-lsp"},
    }
    return payload


# Rule codes that the CodeActionsProvider can repair deterministically.
# Diagnostics with these codes are eligible for `safe_to_auto_apply: true`
# (subject to the provider returning a non-None action).
_REPAIRABLE_RULE_CODES: frozenset[str] = frozenset(
    {
        "NW1001",  # unclosed section -> insert 'end'
        "NW1002",  # unexpected end -> remove stray 'end'
        "NW2001",  # unknown keyword -> typo correction
        "NW2002",  # invalid enum -> suggest closest valid value
        "NW2004",  # missing required section -> insert stub
        "NW2005",  # unknown task theory -> suggest closest
        "NW2006",  # unknown task operation -> suggest closest
        "NW2007",  # unknown basis set -> suggest closest
        "NW2008",  # unknown DFT functional -> suggest closest
        "NW2009",  # unknown top-level directive -> typo correction
        "NW2010",  # duplicate section -> remove the duplicate block
    }
)


def _refusal_reason_for_code(code: str) -> str:
    """Stable rule-scoped refusal reason for codes we cannot auto-repair.

    The string is the contract surface that OpenQC agents and the
    closed-loop test gate match against.
    """
    if code in {"NWCHEM-E044"}:
        return (
            "NWCHEM-E044 is a runtime/output finding; the LSP cannot rewrite the "
            "input deterministically without knowing which iteration failed."
        )
    if code in {"NW2003"}:
        return (
            "NW2003 is a type-mismatch finding; the LSP cannot pick a replacement "
            "value without knowing the caller's scientific intent."
        )
    if code in {"NW2011"}:
        return (
            "NW2011 reports a keyword that is invalid in the current section; the "
            "LSP cannot tell whether to move or delete it without user intent."
        )
    if code in {"NW2012"}:
        return (
            "NW2012 reports malformed atom coordinates; the LSP cannot invent "
            "numeric coordinates without destroying the author's geometry."
        )
    if code in {"NW1003"}:
        return (
            "NW1003 reports an empty section block; the LSP cannot decide whether "
            "to delete the block or leave it as a placeholder."
        )
    return (
        "This diagnostic requires user intent before a safe automatic repair " "can be generated."
    )


def _diagnostic_dict_to_lsp(diag: dict[str, Any]) -> Diagnostic:
    """Rebuild an LSP Diagnostic from the agent CLI's JSON shape."""
    rng = diag.get("range") or {}
    start = rng.get("start") or {}
    end = rng.get("end") or {}
    severity_raw = diag.get("severity", "error")
    severity_map = {
        "error": DiagnosticSeverity.Error,
        "warning": DiagnosticSeverity.Warning,
        "information": DiagnosticSeverity.Information,
        "hint": DiagnosticSeverity.Hint,
    }
    if isinstance(severity_raw, int):
        # lsprotocol enum members are ints, so accept the raw value directly.
        severity = severity_raw  # type: ignore[assignment]
    else:
        severity = severity_map.get(str(severity_raw).lower(), DiagnosticSeverity.Error)
    return Diagnostic(
        range=Range(
            start=Position(
                line=int(start.get("line", 0) or 0),
                character=int(start.get("character", 0) or 0),
            ),
            end=Position(
                line=int(end.get("line", start.get("line", 0) or 0) or 0),
                character=int(end.get("character", start.get("character", 0) or 0) or 0),
            ),
        ),
        message=str(diag.get("message", "")),
        severity=severity,  # type: ignore[arg-type]
        source=str(diag.get("source", "nwchem-lsp")),
        code=str(diag.get("code", "")),
    )


def build_agent_actions(
    source: str,
    diagnostics: list[dict[str, Any]],
    *,
    uri: str = "file:///",
    selected_only: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Return closed-loop agent CLI fix actions for the given diagnostics.

    Args:
        source: Full document text the diagnostics were computed against.
        diagnostics: All diagnostics for the document (JSON shape from the
            agent CLI check operation).
        uri: Document URI used inside WorkspaceEdit changes.
        selected_only: Optional pre-filtered list of diagnostics to act on.
            When provided, only those diagnostics are turned into actions.
            Otherwise every diagnostic in ``diagnostics`` is processed.

    Returns:
        List of action dicts in the agent CLI JSON shape. Each action carries
        ``safe_to_auto_apply``, ``edit`` (dict or ``None``),
        ``refusal_reason`` (str or ``None``), and the diagnostic's stable code.
    """
    provider = CodeActionsProvider()
    selected = selected_only if selected_only is not None else diagnostics
    actions: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for diag in selected:
        code = str(diag.get("code", "") or "")
        lsp_diag = _diagnostic_dict_to_lsp(diag)
        handler_action: Optional[CodeAction] = None
        if code in _REPAIRABLE_RULE_CODES:
            try:
                handler_action = provider._action_for_diagnostic(source, lsp_diag, uri)
            except Exception:
                handler_action = None
        if handler_action is not None and handler_action.edit is not None:
            actions.append(
                code_action_to_agent_json(
                    handler_action,
                    confidence=float(diag.get("confidence", 1.0) or 1.0),
                    blocking=bool(diag.get("blocking", False)),
                    safe_to_auto_apply=True,
                    refusal_reason=None,
                    diagnostic_code=code,
                    diagnostic_range=lsp_diag.range,
                )
            )
            seen_codes.add(code)
            continue
        # Refusal: deterministic repair not available. Surface the rule's
        # stable refusal reason (and the existing fix_hints text) so agents
        # know exactly why the LSP won't auto-rewrite this region.
        hints = diag.get("fix_hints") or []
        if hints:
            for hint in hints[:1]:
                actions.append(
                    {
                        "title": str(hint),
                        "kind": "quickfix",
                        "diagnostic_code": code,
                        "diagnostic_range": _range_to_json(lsp_diag.range),
                        "confidence": float(diag.get("confidence", 1.0) or 1.0),
                        "blocking": bool(diag.get("blocking", False)),
                        "safe_to_auto_apply": False,
                        "edit": None,
                        "refusal_reason": _refusal_reason_for_code(code),
                        "data": {"source": diag.get("source", "nwchem-lsp")},
                    }
                )
        else:
            actions.append(
                {
                    "title": f"Review {code or 'diagnostic'}: {lsp_diag.message}",
                    "kind": "quickfix",
                    "diagnostic_code": code,
                    "diagnostic_range": _range_to_json(lsp_diag.range),
                    "confidence": float(diag.get("confidence", 1.0) or 1.0),
                    "blocking": bool(diag.get("blocking", False)),
                    "safe_to_auto_apply": False,
                    "edit": None,
                    "refusal_reason": _refusal_reason_for_code(code),
                    "data": {"source": diag.get("source", "nwchem-lsp")},
                }
            )
    return actions

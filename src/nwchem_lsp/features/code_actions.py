"""Code actions provider for NWChem LSP.

Provides quick fixes for common NWChem input file errors.
"""

from lsprotocol.types import (
    CodeAction,
    CodeActionKind,
    Diagnostic,
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)

from ..data.keywords import get_all_keyword_names
from ..parser.nwchem_parser import NwchemParser


class CodeActionsProvider:
    """Provides code actions (quick fixes) for NWChem input files."""

    def __init__(self) -> None:
        """Initialize code actions provider."""
        self.valid_keywords = set(get_all_keyword_names())
        self.section_keywords = NwchemParser.SECTION_KEYWORDS

    def get_code_actions(
        self, source: str, diagnostics: list[Diagnostic]
    ) -> list[CodeAction]:
        """Get code actions for the given diagnostics."""
        actions: list[CodeAction] = []

        for diagnostic in diagnostics:
            action = self._get_action_for_diagnostic(source, diagnostic)
            if action:
                actions.append(action)

        actions.extend(self._get_general_actions(source))
        return actions

    def _get_action_for_diagnostic(
        self, source: str, diagnostic: Diagnostic
    ) -> CodeAction | None:
        """Get a code action for a specific diagnostic."""
        message = diagnostic.message.lower()

        if "unclosed section" in message:
            return self._fix_unclosed_section(source, diagnostic)

        if "unexpected 'end'" in message:
            return self._fix_unexpected_end(source, diagnostic)

        if "unknown keyword" in message:
            return self._fix_unknown_keyword(source, diagnostic)

        return None

    def _fix_unclosed_section(self, source: str, diagnostic: Diagnostic) -> CodeAction:
        """Create a fix for unclosed section by adding 'end'."""
        lines = source.split("\n")
        line_num = diagnostic.range.start.line

        section_name = "section"
        if "unclosed section: '" in diagnostic.message.lower():
            parts = diagnostic.message.split("'")
            if len(parts) >= 2:
                section_name = parts[1]

        insert_line = line_num + 1
        while insert_line < len(lines) and lines[insert_line].strip():
            insert_line += 1

        if insert_line >= len(lines):
            insert_position = Position(line=len(lines) - 1, character=len(lines[-1]))
            new_text = "\nend"
        else:
            insert_position = Position(line=insert_line, character=0)
            new_text = "end\n"

        return CodeAction(
            title=f"Add 'end' to close '{section_name}' section",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(start=insert_position, end=insert_position),
                            new_text=new_text,
                        )
                    ]
                }
            ),
        )

    def _fix_unexpected_end(self, source: str, diagnostic: Diagnostic) -> CodeAction | None:
        """Create a fix for unexpected 'end' by removing it."""
        line_num = diagnostic.range.start.line
        lines = source.split("\n")

        if line_num < len(lines):
            line = lines[line_num]
            if line.strip().lower() == "end":
                start_pos = Position(line=line_num, character=0)
                end_pos = Position(line=line_num + 1, character=0)
                return CodeAction(
                    title="Remove unexpected 'end' keyword",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diagnostic],
                    edit=WorkspaceEdit(
                        changes={
                            "document": [
                                TextEdit(
                                    range=Range(start=start_pos, end=end_pos),
                                    new_text="",
                                )
                            ]
                        }
                    ),
                )
        return None

    def _fix_unknown_keyword(
        self, source: str, diagnostic: Diagnostic
    ) -> CodeAction | None:
        """Create a fix for unknown keyword by suggesting a correction."""
        unknown_kw = ""
        if "unknown keyword '" in diagnostic.message.lower():
            parts = diagnostic.message.split("'")
            if len(parts) >= 2:
                unknown_kw = parts[1].lower()

        if not unknown_kw:
            return None

        suggestion = self._find_closest_keyword(unknown_kw)
        if not suggestion:
            return None

        line_num = diagnostic.range.start.line
        col = diagnostic.range.start.character

        return CodeAction(
            title=f"Replace '{unknown_kw}' with '{suggestion}'",
            kind=CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=WorkspaceEdit(
                changes={
                    "document": [
                        TextEdit(
                            range=Range(
                                start=Position(line=line_num, character=col),
                                end=Position(line=line_num, character=col + len(unknown_kw)),
                            ),
                            new_text=suggestion,
                        )
                    ]
                }
            ),
        )

    def _find_closest_keyword(self, unknown: str) -> str | None:
        """Find the closest matching valid keyword."""
        if len(unknown) < 2:
            return None

        typos = {
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
        }

        if unknown in typos:
            return typos[unknown]

        best_match = None
        best_score = 0.0

        for kw in self.valid_keywords:
            score = self._similarity_score(unknown, kw)
            if score > best_score and score > 0.6:
                best_score = score
                best_match = kw

        return best_match

    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity score between two strings (0-1)."""
        if len(s1) > len(s2):
            s1, s2 = s2, s1

        if len(s2) == 0:
            return 1.0 if len(s1) == 0 else 0.0

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1.lower() != c2.lower())
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        distance = previous_row[-1]
        max_len = max(len(s1), len(s2))
        return 1.0 - (distance / max_len)

    def _get_general_actions(self, source: str) -> list[CodeAction]:
        """Get general code actions not tied to specific diagnostics."""
        actions: list[CodeAction] = []

        start_action = self._create_add_start_action(source)
        if start_action:
            actions.append(start_action)

        return actions

    def _create_add_start_action(self, source: str) -> CodeAction | None:
        """Create an action to add missing 'start' directive."""
        lines = source.split("\n")

        for line in lines:
            stripped = line.strip().lower()
            if stripped.startswith("start ") or stripped == "start":
                return None

        return CodeAction(
            title="Add missing 'start' directive",
            kind=CodeActionKind.QuickFix,
            edit=WorkspaceEdit(
                changes={
                    "document": [
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

"""Diagnostics provider for NWChem LSP."""

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

from ..data.keywords import (
    get_all_keyword_names,
    get_keyword_info,
    is_valid_keyword,
)
from ..parser.nwchem_parser import NwchemParser as NWChemParser


class DiagnosticsProvider:
    """Provides diagnostics for NWChem input files."""

    def __init__(self) -> None:
        """Initialize diagnostics provider."""
        self.valid_keywords = set(get_all_keyword_names())

    def get_diagnostics(self, source: str) -> list[Diagnostic]:
        """Get diagnostics for the source."""
        diagnostics: list[Diagnostic] = []

        # Get structural diagnostics
        parser = NWChemParser(source)
        structural = parser.validate()
        for error in structural:
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=error["line"], character=error["column"]),
                        end=Position(line=error["line"], character=error["column"] + 10),
                    ),
                    message=error["message"],
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-lsp",
                )
            )

        # Check each line for unknown keywords
        lines = source.split("\n")
        for line_num, line in enumerate(lines):
            diagnostics.extend(self._check_line(line, line_num))

        return diagnostics

    def _check_line(self, line: str, line_num: int) -> list[Diagnostic]:
        """Check a single line for diagnostics."""
        diagnostics: list[Diagnostic] = []
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            return diagnostics

        # Get first word
        words = stripped.split()
        if not words:
            return diagnostics

        first_word = words[0].lower()

        # Skip if it's a number (geometry data)
        if first_word.replace(".", "").replace("-", "").isdigit():
            return diagnostics

        # Check for unknown keywords
        if first_word not in self.valid_keywords and not first_word.isdigit():
            # Check if it might be an element symbol
            if first_word.capitalize() not in [
                "H",
                "He",
                "Li",
                "Be",
                "B",
                "C",
                "N",
                "O",
                "F",
                "Ne",
            ]:
                col = line.lower().find(first_word)
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=line_num, character=col),
                            end=Position(line=line_num, character=col + len(first_word)),
                        ),
                        message=f"Unknown keyword '{first_word}'",
                        severity=DiagnosticSeverity.Warning,
                        source="nwchem-lsp",
                    )
                )

        # Check for deprecated keywords
        kw_info = get_keyword_info(first_word)
        if kw_info and kw_info.deprecated:
            col = line.lower().find(first_word)
            replacement = kw_info.deprecated_replacement or "alternative"
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=line_num, character=col),
                        end=Position(line=line_num, character=col + len(first_word)),
                    ),
                    message=f"Deprecated keyword '{first_word}'. Use '{replacement}' instead.",
                    severity=DiagnosticSeverity.Warning,
                    source="nwchem-lsp",
                )
            )

        # Check argument count
        if kw_info and kw_info.args:
            min_args = len(kw_info.args)
            actual_args = len(words) - 1
            if actual_args < min_args:
                col = len(line) - len(stripped)
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=line_num, character=col),
                            end=Position(line=line_num, character=len(line)),
                        ),
                        message=f"'{first_word}' requires at least {min_args} argument(s)",
                        severity=DiagnosticSeverity.Error,
                        source="nwchem-lsp",
                    )
                )

        # Check allowed values
        if kw_info and kw_info.allowed_values and len(words) > 1:
            arg_value = words[1].lower()
            if arg_value not in [v.lower() for v in kw_info.allowed_values]:
                col = line.lower().find(words[1].lower())
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=line_num, character=col),
                            end=Position(line=line_num, character=col + len(words[1])),
                        ),
                        message=f"Invalid value '{arg_value}'. "
                        f"Allowed: {', '.join(kw_info.allowed_values)}",
                        severity=DiagnosticSeverity.Error,
                        source="nwchem-lsp",
                    )
                )

        return diagnostics

    def _get_line_range(self, line_num: int, line: str) -> Range:
        """Get a range for the entire line."""
        return Range(
            start=Position(line=line_num, character=0),
            end=Position(line=line_num, character=len(line)),
        )

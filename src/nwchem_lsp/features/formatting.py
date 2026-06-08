"""LSP formatting provider for NWChem.

This module provides document and range formatting for NWChem input files,
including section indentation, keyword normalization, comment preservation,
and nested section support.
"""

from __future__ import annotations

from typing import List, Optional

from lsprotocol.types import (
    DocumentFormattingParams,
    DocumentRangeFormattingParams,
    FormattingOptions,
    Position,
    Range,
    TextEdit,
)
from pygls.server import LanguageServer

from ..data.keywords import DFT_FUNCTIONALS, TASK_OPERATIONS, TOP_LEVEL_SECTIONS


class NwchemFormattingProvider:
    """Provides formatting for NWChem input files.

    Handles:
    - Consistent indentation of section bodies
    - Keyword normalization (lowercase section names and keywords)
    - Preservation of comments, blank lines, and element symbols
    - Nested section indentation
    - Range formatting for partial document edits
    """

    # Keywords that should be normalized to lowercase
    _NORMALIZE_KEYWORDS: frozenset[str] = frozenset(
        {"end", "library"}
        | {s.lower() for s in TOP_LEVEL_SECTIONS}
        | {s.lower() for s in DFT_FUNCTIONALS}
        | {s.lower() for s in TASK_OPERATIONS}
        | {
            "start", "restart", "title", "echo", "set", "unset", "stop",
            "task", "charge", "memory", "permanent_dir", "scratch_dir",
            "print",
            # SCF keywords
            "singlet", "doublet", "triplet", "quartet", "quintet",
            "rhf", "uhf", "rohf", "thresh", "maxiter", "direct", "semidirect",
            # DFT keywords
            "xc", "grid", "convergence", "iterations", "noio", "odft", "mult",
            "coarse", "medium", "fine", "xfine", "ultrafine",
            # Geometry keywords
            "units", "angstroms", "bohr", "au", "autosym", "noautoz",
            "center", "nocenter", "system",
            # Basis keywords
            "spherical", "cartesian", "file",
            # MP2 keywords
            "tight", "freeze", "ri", "cd",
            # CC keywords
            "tce", "diis",
            # General
            "total", "stack", "heap", "global",
            "none", "low", "high", "debug",
            # Task theories
            "scf", "dft", "mp2", "ccsd", "ccsd(t)", "mcscf", "semi", "rimp2",
            # Grid keywords for convergence
            "energy", "density", "gradient",
        }
    )

    def __init__(self, server: LanguageServer) -> None:
        """Initialize the formatting provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def format_document(
        self, text: str, params: DocumentFormattingParams
    ) -> List[TextEdit]:
        """Format the entire document.

        Args:
            text: Document text
            params: Formatting parameters

        Returns:
            List of text edits to apply
        """
        options = params.options or FormattingOptions(tab_size=2, insert_spaces=True)
        formatted = self._format_text(text, options)

        if formatted == text:
            return []

        lines = text.splitlines()
        return [
            TextEdit(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=len(lines), character=0),
                ),
                new_text=formatted,
            )
        ]

    def format_range(
        self, text: str, params: DocumentRangeFormattingParams
    ) -> List[TextEdit]:
        """Format a specific range of the document.

        For range formatting, the provider formats only the selected line range.
        It determines the correct indentation context by scanning from the
        document start so that nested sections are respected.

        Args:
            text: Document text
            params: Range formatting parameters

        Returns:
            List of text edits to apply
        """
        options = params.options or FormattingOptions(tab_size=2, insert_spaces=True)
        all_lines = text.splitlines()

        start_line = params.range.start.line
        end_line = params.range.end.line

        # Clamp to valid range
        start_line = max(0, start_line)
        end_line = min(len(all_lines) - 1, end_line)

        if start_line > end_line:
            return []

        # Compute indent context from the beginning of the document
        # so we know the correct nesting level at the range start.
        indent_str = " " * options.tab_size if options.insert_spaces else "\t"
        indent_level = self._compute_indent_at_line(all_lines, start_line)

        edits: List[TextEdit] = []

        for i in range(start_line, end_line + 1):
            if i >= len(all_lines):
                break

            original = all_lines[i]
            formatted = self._format_line(original, indent_level, indent_str)

            if formatted != original:
                line_length = len(original)
                edits.append(
                    TextEdit(
                        range=Range(
                            start=Position(line=i, character=0),
                            end=Position(line=i, character=line_length),
                        ),
                        new_text=formatted,
                    )
                )

            # Update indent level for next line based on this line
            indent_level = self._update_indent_level(
                formatted.strip(), indent_level
            )

        return edits

    def _format_text(self, text: str, options: FormattingOptions) -> str:
        """Format the full text and return the formatted version.

        Args:
            text: Full document text
            options: Formatting options

        Returns:
            Formatted text
        """
        lines = text.splitlines()
        indent_str = " " * options.tab_size if options.insert_spaces else "\t"
        indent_level = 0
        formatted_lines: List[str] = []

        for line in lines:
            stripped = line.strip()

            # Empty lines: preserve as blank
            if not stripped:
                formatted_lines.append("")
                continue

            # Comments: preserve content, strip leading whitespace only
            if stripped.startswith("#"):
                formatted_lines.append(stripped)
                continue

            # End keyword: decrease indent before formatting
            if stripped.lower() == "end":
                indent_level = max(0, indent_level - 1)
                formatted_lines.append(
                    indent_str * indent_level + self._normalize_line(stripped)
                )
                continue

            # Section start: format at current level, increase indent for children
            parts = stripped.split()
            if parts and parts[0].lower() in TOP_LEVEL_SECTIONS:
                normalized = self._normalize_section_header(stripped)
                formatted_lines.append(indent_str * indent_level + normalized)
                indent_level += 1
                continue

            # Regular content line: apply current indentation
            normalized = self._normalize_line(stripped)
            formatted_lines.append(indent_str * indent_level + normalized)

        result = "\n".join(formatted_lines)
        if text.endswith("\n"):
            result += "\n"

        return result

    def _format_line(
        self, stripped_line: str, indent_level: int, indent_str: str
    ) -> str:
        """Format a single line with the given indent level.

        Args:
            stripped_line: The stripped content of the line
            indent_level: Current indentation level
            indent_str: Indentation string (spaces or tab)

        Returns:
            Formatted line
        """
        stripped = stripped_line.strip()

        if not stripped:
            return ""

        if stripped.startswith("#"):
            return stripped

        if stripped.lower() == "end":
            level = max(0, indent_level - 1)
            return indent_str * level + self._normalize_line(stripped)

        parts = stripped.split()
        if parts and parts[0].lower() in TOP_LEVEL_SECTIONS:
            return indent_str * indent_level + self._normalize_section_header(stripped)

        return indent_str * indent_level + self._normalize_line(stripped)

    @staticmethod
    def _compute_indent_at_line(lines: List[str], target_line: int) -> int:
        """Compute the indentation level at a target line by scanning from the top.

        Args:
            lines: All lines in the document
            target_line: The line to compute indent level for

        Returns:
            Indentation level at the start of target_line
        """
        indent_level = 0

        for i in range(target_line):
            if i >= len(lines):
                break

            stripped = lines[i].strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.lower() == "end":
                indent_level = max(0, indent_level - 1)
            else:
                parts = stripped.split()
                if parts and parts[0].lower() in TOP_LEVEL_SECTIONS:
                    indent_level += 1

        return indent_level

    @staticmethod
    def _update_indent_level(
        stripped_line: str, current_level: int
    ) -> int:
        """Update indent level after processing a line.

        Args:
            stripped_line: Stripped line content
            current_level: Current indent level

        Returns:
            Updated indent level for the next line
        """
        if not stripped_line or stripped_line.startswith("#"):
            return current_level

        if stripped_line.lower() == "end":
            return max(0, current_level - 1)

        parts = stripped_line.split()
        if parts and parts[0].lower() in TOP_LEVEL_SECTIONS:
            return current_level + 1

        return current_level

    def _normalize_line(self, line: str) -> str:
        """Normalize keyword casing in a line, preserving inter-token spacing.

        Tokens that match known keywords are lowercased in-place, keeping the
        original whitespace between tokens intact.

        Args:
            line: Stripped line content

        Returns:
            Normalized line
        """
        if not line:
            return line

        # Tokenize while preserving whitespace boundaries
        result: List[str] = []
        i = 0
        n = len(line)

        while i < n:
            # Capture leading whitespace
            ws_start = i
            while i < n and line[i] in (" ", "\t"):
                i += 1
            if i > ws_start:
                result.append(line[ws_start:i])

            # Capture the token
            tok_start = i
            while i < n and line[i] not in (" ", "\t"):
                i += 1
            if i > tok_start:
                token = line[tok_start:i]
                lower = token.lower()
                if lower in self._NORMALIZE_KEYWORDS:
                    result.append(lower)
                else:
                    result.append(token)

        return "".join(result)

    def _normalize_section_header(self, line: str) -> str:
        """Normalize a section header line, preserving inter-token spacing.

        The section keyword is lowercased; arguments after it are normalized
        individually (known options lowercased, values preserved).

        Args:
            line: Stripped section header line

        Returns:
            Normalized section header
        """
        if not line:
            return line

        # Tokenize while preserving whitespace boundaries
        result: List[str] = []
        i = 0
        n = len(line)
        first_token = True

        while i < n:
            # Capture leading whitespace
            ws_start = i
            while i < n and line[i] in (" ", "\t"):
                i += 1
            if i > ws_start:
                result.append(line[ws_start:i])

            # Capture the token
            tok_start = i
            while i < n and line[i] not in (" ", "\t"):
                i += 1
            if i > tok_start:
                token = line[tok_start:i]
                if first_token:
                    # Section keyword is always lowercased
                    result.append(token.lower())
                    first_token = False
                else:
                    lower = token.lower()
                    if lower in self._NORMALIZE_KEYWORDS:
                        result.append(lower)
                    else:
                        result.append(token)

        return "".join(result)


# Alias for backwards compatibility
FormattingProvider = NwchemFormattingProvider


def get_formatting_provider(server: LanguageServer) -> NwchemFormattingProvider:
    """Create a formatting provider instance.

    Args:
        server: The language server instance

    Returns:
        Formatting provider instance
    """
    return NwchemFormattingProvider(server)

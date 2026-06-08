"""Schema-aware static lint checks for NWChem input files.

Produces LSP diagnostics with stable rule codes organized into three
categories:

- **NW**** syntax errors** -- parse-level problems (unclosed sections,
  unexpected END)
- **NW**** schema violations** -- unknown keywords, invalid enum values,
  type mismatches, missing required directives, cross-section
  inconsistencies
- **NW**** best-practice warnings** -- suspicious values, deprecated
  keywords, configuration smells

Rule codes are prefixed with ``NW`` and a numeric category:

=========  =====  ==============================================
Category   Range  Example
=========  =====  ==============================================
Syntax     1000   NW1001 Unclosed section
Schema     2000   NW2001 Unknown keyword in section
Hint       3000   NW3001 Unusual convergence threshold
=========  =====  ==============================================

The full rule catalog is available at :attr:`RULE_DESCRIPTIONS`.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)

from ..data.keywords import (
    ALL_KEYWORDS,
    BASIS_SETS,
    DFT_FUNCTIONALS,
    ELEMENTS,
    TASK_OPERATIONS,
    TASK_THEORIES,
    TOP_LEVEL_SECTIONS,
)
from ..parser.nwchem_parser import NWchemSection, NwchemParser

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Rule code registry
# ------------------------------------------------------------------

RULE_DESCRIPTIONS: dict[str, str] = {
    # -- Syntax (1000-1099) --
    "NW1001": "Unclosed section",
    "NW1002": "Unexpected 'end' without matching section",
    "NW1003": "Empty section block",
    # -- Schema (2000-2999) --
    "NW2001": "Unknown keyword inside section",
    "NW2002": "Invalid enum value for keyword",
    "NW2003": "Type mismatch for keyword argument",
    "NW2004": "Missing required section",
    "NW2005": "Unknown task theory",
    "NW2006": "Unknown task operation",
    "NW2007": "Unknown basis set name",
    "NW2008": "Unknown DFT functional",
    "NW2009": "Unknown top-level directive",
    "NW2010": "Duplicate section (only one allowed)",
    "NW2011": "Keyword not valid in this section",
    # -- Best-practice / hints (3000-3999) --
    "NW3001": "SCF maxiter outside typical range (1-500)",
    "NW3002": "Convergence threshold unusually loose",
    "NW3003": "Duplicate task directive",
    "NW3004": "Unusual charge/multiplicity combination",
}

# Sections that may appear at most once
_SINGLETON_SECTIONS: set[str] = {"geometry", "scf", "dft", "mp2", "ccsd"}

# Set of top-level section names for fast lookup
_TOP_LEVEL_SECTIONS_SET: set[str] = set(TOP_LEVEL_SECTIONS)

# Set of element symbols in lowercase for fast lookup
_ELEMENTS_LOWER: set[str] = {e.lower() for e in ELEMENTS}

# Set of basis set names in lowercase for fast lookup
_BASIS_SETS_LOWER: set[str] = {b.lower() for b in BASIS_SETS}

# Set of DFT functional names in lowercase for fast lookup
_DFT_FUNCTIONALS_LOWER: set[str] = {f.lower() for f in DFT_FUNCTIONALS}

# Set of task theories in lowercase
_TASK_THEORIES_LOWER: set[str] = {t.lower() for t in TASK_THEORIES}

# Set of task operations in lowercase
_TASK_OPERATIONS_LOWER: set[str] = {o.lower() for o in TASK_OPERATIONS}


def _range_at(line: int, char_start: int, char_end: int) -> Range:
    """Build an LSP Range."""
    return Range(
        start=Position(line=line, character=char_start),
        end=Position(line=line, character=char_end),
    )


def _diag(
    line: int,
    char_start: int,
    char_end: int,
    message: str,
    severity: DiagnosticSeverity,
    code: str,
) -> Diagnostic:
    """Create a Diagnostic with a stable rule code."""
    return Diagnostic(
        range=_range_at(line, char_start, char_end),
        message=message,
        severity=severity,
        source="nwchem-lsp",
        code=code,
    )


def _find_col(haystack: str, needle: str, start: int = 0) -> int:
    """Find column position of needle in haystack (case-insensitive), starting from `start`."""
    idx = haystack.lower().find(needle, start)
    return max(idx, 0)


class NwchemLintProvider:
    """Schema-aware static lint for NWChem inputs.

    Runs deterministic, offline checks against the curated keyword
    metadata in :mod:`nwchem_lsp.data.keywords` and reports findings
    as standard LSP diagnostics with stable rule codes.
    """

    def __init__(self) -> None:
        """Initialize lint provider."""

    def lint(self, text: str) -> list[Diagnostic]:
        """Run all lint checks and return diagnostics.

        Args:
            text: Full NWChem input file text.

        Returns:
            List of LSP Diagnostic objects with rule codes.
        """
        diagnostics: list[Diagnostic] = []
        lines = text.split("\n")

        parser = NwchemParser(text)
        sections = parser.sections

        # Syntax checks
        self._check_syntax(lines, diagnostics)

        # Schema checks
        self._check_required_sections(sections, diagnostics)
        self._check_singleton_sections(sections, lines, diagnostics)
        self._check_keywords_in_sections(sections, lines, diagnostics)
        self._check_task_directives(lines, diagnostics)
        self._check_basis_references(sections, lines, diagnostics)
        self._check_dft_functionals(sections, lines, diagnostics)
        self._check_top_level_directives(lines, sections, diagnostics)

        # Best-practice checks
        self._check_scf_maxiter(sections, lines, diagnostics)
        self._check_convergence_thresh(sections, lines, diagnostics)
        self._check_duplicate_tasks(lines, diagnostics)

        return diagnostics

    # ------------------------------------------------------------------
    # Syntax checks (NW1xxx)
    # ------------------------------------------------------------------

    def _check_syntax(
        self, lines: list[str], diagnostics: list[Diagnostic]
    ) -> None:
        """Check for parse-level syntax problems."""
        open_stack: list[tuple[str, int]] = []

        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if not parts:
                continue

            keyword = parts[0]

            if keyword in _TOP_LEVEL_SECTIONS_SET:
                open_stack.append((keyword, i))

            elif keyword == "end":
                if not open_stack:
                    col = _find_col(line, "end")
                    diagnostics.append(
                        _diag(
                            i,
                            col,
                            col + 3,
                            "Unexpected 'end' without matching section",
                            DiagnosticSeverity.Error,
                            "NW1002",
                        )
                    )
                else:
                    open_stack.pop()

        for section_name, start_line in open_stack:
            col = _find_col(lines[start_line], section_name)
            diagnostics.append(
                _diag(
                    start_line,
                    col,
                    col + len(section_name),
                    f"Unclosed section: '{section_name}'",
                    DiagnosticSeverity.Error,
                    "NW1001",
                )
            )

    # ------------------------------------------------------------------
    # Schema checks (NW2xxx)
    # ------------------------------------------------------------------

    def _check_required_sections(
        self, sections: dict[str, list[Any]], diagnostics: list[Diagnostic]
    ) -> None:
        """Report missing required sections."""
        for name in ("geometry", "basis"):
            if name not in sections:
                diagnostics.append(
                    _diag(
                        0, 0, 0,
                        f"Missing required '{name}' block",
                        DiagnosticSeverity.Error,
                        "NW2004",
                    )
                )

    def _check_singleton_sections(
        self,
        sections: dict[str, list[Any]],
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Flag sections that should appear at most once."""
        for name in _SINGLETON_SECTIONS:
            if name in sections and len(sections[name]) > 1:
                section_obj = sections[name][1]
                line = section_obj.start_line
                col = _find_col(lines[line], name) if line < len(lines) else 0
                diagnostics.append(
                    _diag(
                        line,
                        col,
                        col + len(name),
                        f"Duplicate '{name}' section (only one allowed)",
                        DiagnosticSeverity.Warning,
                        "NW2010",
                    )
                )

    def _check_keywords_in_sections(
        self,
        sections: dict[str, list[Any]],
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Validate keywords against the schema for their enclosing section."""
        for section_name, section_list in sections.items():
            schema_key = self._section_to_schema_key(section_name)
            valid_keywords = self._get_valid_keywords_for_section(schema_key)

            for section_obj in section_list:
                for idx, content_line in enumerate(section_obj.content):
                    stripped = content_line.strip().lower()
                    if not stripped or stripped.startswith("#") or stripped == "end":
                        continue

                    parts = stripped.split()
                    if not parts:
                        continue

                    kw = parts[0]

                    # Section header line (e.g. "geometry units angstroms"):
                    # validate arguments after the section name, then skip.
                    if kw == section_name:
                        if len(parts) > 1:
                            self._validate_section_header_args(
                                section_name, parts[1:],
                                section_obj.start_line + idx,
                                content_line, diagnostics,
                            )
                        continue

                    # Skip known sub-patterns (atom coords, element specs, etc.)
                    if self._is_data_line(section_name, parts):
                        continue

                    # Check keyword validity against schema
                    if valid_keywords and kw not in valid_keywords:
                        line_num = section_obj.start_line + idx
                        col = _find_col(content_line, kw)
                        diagnostics.append(
                            _diag(
                                line_num,
                                col,
                                col + len(kw),
                                f"Unknown keyword '{kw}' in {section_name} section",
                                DiagnosticSeverity.Warning,
                                "NW2001",
                            )
                        )

                    # Enum validation for known keywords with allowed values
                    self._check_enum_value(
                        kw, parts, section_name, section_obj.start_line + idx,
                        content_line, diagnostics,
                    )

    def _check_enum_value(
        self,
        kw: str,
        parts: list[str],
        section_name: str,
        line_num: int,
        raw_line: str,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Validate enum values for keywords with known allowed values."""
        if len(parts) < 2:
            return

        value = parts[1]
        kw_col = _find_col(raw_line, kw)
        col = _find_col(raw_line, value, kw_col + len(kw))

        # DFT XC functional validation
        if kw == "xc" and section_name == "dft":
            if value.lower() not in _DFT_FUNCTIONALS_LOWER:
                diagnostics.append(
                    _diag(
                        line_num, col, col + len(value),
                        f"Unknown DFT functional '{value}'",
                        DiagnosticSeverity.Warning,
                        "NW2008",
                    )
                )

        # Grid enum validation
        elif kw == "grid" and section_name == "dft":
            valid_grids = {"coarse", "medium", "fine", "xfine", "ultrafine"}
            if value.lower() not in valid_grids:
                diagnostics.append(
                    _diag(
                        line_num, col, col + len(value),
                        f"Invalid grid value '{value}' (expected one of: "
                        f"{', '.join(sorted(valid_grids))})",
                        DiagnosticSeverity.Warning,
                        "NW2002",
                    )
                )

        # Basis library enum validation
        elif kw == "library" and section_name in ("basis", "ecp"):
            if value.lower() not in _BASIS_SETS_LOWER:
                diagnostics.append(
                    _diag(
                        line_num, col, col + len(value),
                        f"Unknown basis set '{value}'",
                        DiagnosticSeverity.Warning,
                        "NW2007",
                    )
                )

        # Units enum validation in geometry
        elif kw == "units" and section_name == "geometry":
            valid_units = {"angstroms", "bohr", "nanometers", "picometers", "au"}
            if value.lower() not in valid_units:
                diagnostics.append(
                    _diag(
                        line_num, col, col + len(value),
                        f"Invalid units '{value}' (expected one of: "
                        f"{', '.join(sorted(valid_units))})",
                        DiagnosticSeverity.Warning,
                        "NW2002",
                    )
                )

    def _check_task_directives(
        self, lines: list[str], diagnostics: list[Diagnostic]
    ) -> None:
        """Validate task directives for theory and operation."""
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if not stripped.startswith("task") or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 2:
                continue

            theory = parts[1]
            task_col = _find_col(line, "task")
            col = _find_col(line, theory, task_col + 4)
            if theory not in _TASK_THEORIES_LOWER:
                diagnostics.append(
                    _diag(
                        i, col, col + len(theory),
                        f"Unknown task theory '{theory}' (expected one of: "
                        f"{', '.join(sorted(_TASK_THEORIES_LOWER))})",
                        DiagnosticSeverity.Error,
                        "NW2005",
                    )
                )

            if len(parts) >= 3:
                operation = parts[2]
                op_col = _find_col(line, operation, col + len(theory))
                if operation not in _TASK_OPERATIONS_LOWER:
                    diagnostics.append(
                        _diag(
                            i, op_col, op_col + len(operation),
                            f"Unknown task operation '{operation}'",
                            DiagnosticSeverity.Warning,
                            "NW2006",
                        )
                    )

    def _check_basis_references(
        self,
        sections: dict[str, list[Any]],
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Validate basis set library references against known set."""
        if "basis" not in sections:
            return

        for section_obj in sections["basis"]:
            for idx, content_line in enumerate(section_obj.content):
                stripped = content_line.strip().lower()
                if "library" not in stripped:
                    continue

                match = re.search(r"library\s+(\S+)", stripped)
                if match:
                    basis_name = match.group(1)
                    if basis_name.lower() not in _BASIS_SETS_LOWER:
                        line_num = section_obj.start_line + idx
                        col = _find_col(content_line, basis_name)
                        diagnostics.append(
                            _diag(
                                line_num, col, col + len(basis_name),
                                f"Unknown basis set '{basis_name}'",
                                DiagnosticSeverity.Warning,
                                "NW2007",
                            )
                        )

    def _check_dft_functionals(
        self,
        sections: dict[str, list[Any]],
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Validate DFT XC functional names."""
        if "dft" not in sections:
            return

        for section_obj in sections["dft"]:
            for idx, content_line in enumerate(section_obj.content):
                stripped = content_line.strip().lower()
                if not stripped.startswith("xc"):
                    continue

                parts = stripped.split()
                if len(parts) >= 2:
                    functional = parts[1]
                    if functional.lower() not in _DFT_FUNCTIONALS_LOWER:
                        line_num = section_obj.start_line + idx
                        col = _find_col(content_line, functional)
                        diagnostics.append(
                            _diag(
                                line_num, col, col + len(functional),
                                f"Unknown DFT functional '{functional}'",
                                DiagnosticSeverity.Warning,
                                "NW2008",
                            )
                        )

    def _check_top_level_directives(
        self,
        lines: list[str],
        sections: dict[str, list[Any]],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Flag unknown top-level directives (not sections, not task)."""
        known_directives = NwchemParser.TOP_LEVEL_KEYWORDS | _TOP_LEVEL_SECTIONS_SET

        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if not parts:
                continue

            keyword = parts[0]

            # Skip if inside a section
            in_section = False
            for section_list in sections.values():
                for section_obj in section_list:
                    end = (
                        section_obj.end_line
                        if section_obj.end_line is not None
                        else len(lines)
                    )
                    if section_obj.start_line <= i <= end:
                        in_section = True
                        break
                if in_section:
                    break

            if in_section:
                continue

            if keyword not in known_directives:
                col = _find_col(line, keyword)
                diagnostics.append(
                    _diag(
                        i, col, col + len(keyword),
                        f"Unknown top-level directive '{keyword}'",
                        DiagnosticSeverity.Warning,
                        "NW2009",
                    )
                )

    # ------------------------------------------------------------------
    # Best-practice checks (NW3xxx)
    # ------------------------------------------------------------------

    def _check_scf_maxiter(
        self,
        sections: dict[str, list[Any]],
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Flag SCF maxiter values outside typical range."""
        if "scf" not in sections:
            return

        for section_obj in sections["scf"]:
            for idx, content_line in enumerate(section_obj.content):
                stripped = content_line.strip().lower()
                if not stripped.startswith("maxiter"):
                    continue

                parts = stripped.split()
                if len(parts) < 2:
                    continue

                try:
                    maxiter = int(parts[1])
                except ValueError:
                    line_num = section_obj.start_line + idx
                    col = _find_col(content_line, parts[1])
                    diagnostics.append(
                        _diag(
                            line_num, col, col + len(parts[1]),
                            f"Non-integer maxiter value: '{parts[1]}'",
                            DiagnosticSeverity.Error,
                            "NW2003",
                        )
                    )
                    continue

                if maxiter < 1 or maxiter > 500:
                    line_num = section_obj.start_line + idx
                    col = _find_col(content_line, parts[1])
                    diagnostics.append(
                        _diag(
                            line_num, col, col + len(parts[1]),
                            f"SCF maxiter ({maxiter}) outside typical range 1-500",
                            DiagnosticSeverity.Hint,
                            "NW3001",
                        )
                    )

    def _check_convergence_thresh(
        self,
        sections: dict[str, list[Any]],
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Flag unusually loose convergence thresholds."""
        if "scf" not in sections:
            return

        for section_obj in sections["scf"]:
            for idx, content_line in enumerate(section_obj.content):
                stripped = content_line.strip().lower()
                if not stripped.startswith("thresh"):
                    continue

                parts = stripped.split()
                if len(parts) < 2:
                    continue

                try:
                    thresh = float(parts[1])
                except ValueError:
                    continue

                if thresh > 1e-4:
                    line_num = section_obj.start_line + idx
                    col = _find_col(content_line, parts[1])
                    diagnostics.append(
                        _diag(
                            line_num, col, col + len(parts[1]),
                            f"Convergence threshold ({thresh}) is unusually loose "
                            f"(typical: < 1e-4)",
                            DiagnosticSeverity.Hint,
                            "NW3002",
                        )
                    )

    def _check_duplicate_tasks(
        self, lines: list[str], diagnostics: list[Diagnostic]
    ) -> None:
        """Flag duplicate task directives."""
        task_lines: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if stripped.startswith("task ") and not stripped.startswith("#"):
                task_lines.append((i, stripped))

        if len(task_lines) > 1:
            for line_num, _ in task_lines[1:]:
                col = _find_col(lines[line_num], "task")
                diagnostics.append(
                    _diag(
                        line_num, col, col + 4,
                        "Duplicate task directive (NWChem uses the last one)",
                        DiagnosticSeverity.Information,
                        "NW3003",
                    )
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _section_to_schema_key(self, section_name: str) -> str:
        """Map a parser section name to the keyword schema section key."""
        mapping = {
            "dft": "dft",
            "scf": "scf",
            "geometry": "geometry",
            "basis": "basis",
            "mp2": "mp2",
            "ccsd": "cc",
            "ccsd(t)": "cc",
            "ecp": "basis",
            "charge": "charge",
        }
        return mapping.get(section_name, "")

    def _get_valid_keywords_for_section(self, schema_key: str) -> set[str]:
        """Get the set of valid keyword names for a schema section."""
        section_dict = ALL_KEYWORDS.get(schema_key, {})
        return set(section_dict.keys())

    def _is_data_line(self, section_name: str, parts: list[str]) -> bool:
        """Return True if the line is a data line, not a keyword line."""
        if section_name == "geometry":
            # Atom coordinate lines: Element x y z
            if len(parts) >= 4:
                try:
                    float(parts[1])
                    return True
                except ValueError:
                    pass
            # Geometry sub-specifiers treated as data (not keyword lines)
            if parts[0] in {
                "angstroms", "bohr", "au", "nocenter", "center",
                "autosym", "noautoz", "system",
            }:
                return True

        if section_name == "basis":
            # Element library basis-set or element-specific basis
            if parts[0] in _ELEMENTS_LOWER:
                return True
            if parts[0] == "*":
                return True

        if section_name in ("ecp",):
            if parts[0] in _ELEMENTS_LOWER:
                return True

        return False

    def _validate_section_header_args(
        self,
        section_name: str,
        args: list[str],
        line_num: int,
        raw_line: str,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Validate arguments on the section header line.

        For example ``geometry units parsecs`` -- the ``units parsecs``
        part needs enum validation even though the line starts with the
        section name.
        """
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "units" and section_name == "geometry" and i + 1 < len(args):
                value = args[i + 1]
                valid_units = {"angstroms", "bohr", "nanometers", "picometers", "au"}
                if value.lower() not in valid_units:
                    col = _find_col(raw_line, value)
                    diagnostics.append(
                        _diag(
                            line_num, col, col + len(value),
                            f"Invalid units '{value}' (expected one of: "
                            f"{', '.join(sorted(valid_units))})",
                            DiagnosticSeverity.Warning,
                            "NW2002",
                        )
                    )
                i += 2
            elif arg == "spherical" and section_name == "basis":
                i += 1  # valid flag
            elif arg == "cartesian" and section_name == "basis":
                i += 1  # valid flag
            else:
                i += 1



__all__ = ["NwchemLintProvider", "RULE_DESCRIPTIONS"]

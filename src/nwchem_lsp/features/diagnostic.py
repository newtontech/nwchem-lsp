"""LSP diagnostic provider for NWChem."""

from __future__ import annotations

import json
from typing import Any

from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)
from pygls.server import LanguageServer

from ..data.keywords import ALL_KEYWORDS, get_keyword
from ..exceptions import ParseError, ValidationError
from ..parser.nwchem_parser import NwchemParser as NWChemParser
from ..parser.nwchem_parser import NWchemSection

from .lint import NwchemLintProvider

# Mapping from DiagnosticSeverity enum to human-readable strings.
_SEVERITY_NAMES: dict[int, str] = {
    DiagnosticSeverity.Error: "error",
    DiagnosticSeverity.Warning: "warning",
    DiagnosticSeverity.Information: "information",
    DiagnosticSeverity.Hint: "hint",
}


class DiagnosticProvider:
    """Provider for NWChem diagnostics."""

    # Valid basis sets
    VALID_BASIS_SETS = {
        "sto-3g",
        "3-21g",
        "6-31g",
        "6-31g*",
        "6-31g**",
        "6-311g",
        "6-311g*",
        "6-311g**",
        "6-311+g*",
        "6-311++g**",
        "cc-pvdz",
        "cc-pvtz",
        "cc-pvqz",
        "cc-pv5z",
        "aug-cc-pvdz",
        "aug-cc-pvtz",
        "aug-cc-pvqz",
        "aug-cc-pv5z",
        "def2-svp",
        "def2-tzvp",
        "def2-qzvp",
        "lanl2dz",
        "sdd",
    }

    # Valid DFT functionals
    VALID_XC_FUNCTIONALS = {
        "slater",
        "vwn_5",
        "vwn_1",
        "pbe",
        "pbex",
        "pbec",
        "b3lyp",
        "pbe0",
        "camb3lyp",
        "wb97x-d",
        "m06-l",
        "m06-2x",
        "blyp",
        "bp86",
        "bpw91",
        "olyp",
        "opbe",
        "revpbe",
        "hfexch",
        "becke88",
        "lyp",
        "pw91",
        "optx",
    }

    # Valid task operations
    VALID_TASK_OPERATIONS = {
        "energy",
        "optimize",
        "saddle",
        "hessian",
        "frequencies",
        "dynamics",
        "property",
        "raman",
        "dipole",
        "gradient",
    }

    def __init__(self, server: LanguageServer) -> None:
        """Initialize diagnostic provider.

        Args:
            server: The language server instance.
        """
        self.server = server
        # Per-URI cache of the most recent diagnostics, used for snapshots.
        self._diagnostics_cache: dict[str, list[Diagnostic]] = {}
        # Schema-aware lint provider
        self.lint_provider = NwchemLintProvider()

    def get_diagnostics(self, text: str) -> list[Diagnostic]:
        """Get diagnostics for the document.

        Args:
            text: Document text.

        Returns:
            List of diagnostics.
        """
        diagnostics: list[Diagnostic] = []

        try:
            parser = NWChemParser(text)
            blocks = parser.parse()
        except (ParseError, ValidationError) as exc:
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0), end=Position(line=0, character=1),
                    ),
                    message=str(exc),
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-lsp",
                )
            )
            return diagnostics
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0), end=Position(line=0, character=1),
                    ),
                    message=f"Parser error: {exc}",
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-lsp",
                )
            )
            return diagnostics

        lines = text.split("\n")

        # Check for required blocks
        self._check_required_blocks(blocks, diagnostics)

        # Schema-aware lint checks
        try:
            lint_diagnostics = self.lint_provider.lint(text)
            diagnostics.extend(lint_diagnostics)
        except Exception:
            logger.exception("Error running lint checks")

        # Check each block
        for block in blocks:
            self._check_block(block, lines, diagnostics)

        return diagnostics

    def update_cache(self, uri: str, diagnostics: list[Diagnostic]) -> None:
        """Store diagnostics in the per-URI cache.

        Called by the server after every publish_diagnostics so snapshots
        always reflect the latest state.

        Args:
            uri: Document URI.
            diagnostics: Diagnostics to cache.
        """
        self._diagnostics_cache[uri] = list(diagnostics)

    # ------------------------------------------------------------------
    # Snapshot API
    # ------------------------------------------------------------------

    def _diagnostic_to_dict(self, diag: Diagnostic) -> dict[str, Any]:
        """Convert an LSP Diagnostic to a JSON-serializable dict.

        The output is deterministic: fields are ordered and severity is
        represented as both a numeric code and a human-readable string.

        Args:
            diag: LSP Diagnostic object.

        Returns:
            JSON-serializable dictionary.
        """
        severity_value = diag.severity if diag.severity is not None else DiagnosticSeverity.Error
        return {
            "range": {
                "start": {
                    "line": diag.range.start.line,
                    "character": diag.range.start.character,
                },
                "end": {
                    "line": diag.range.end.line,
                    "character": diag.range.end.character,
                },
            },
            "severity": severity_value,
            "severity_label": _SEVERITY_NAMES.get(severity_value, "unknown"),
            "source": diag.source or "nwchem-lsp",
            "code": str(diag.code) if diag.code is not None else None,
            "message": diag.message,
        }

    def get_diagnostics_snapshot(self, uri: str) -> list[dict[str, Any]]:
        """Return a JSON-serializable snapshot of diagnostics for a single URI.

        The snapshot reflects the most recently published diagnostics for the
        document.  Returns an empty list when the URI has not been seen.

        Args:
            uri: Document URI.

        Returns:
            List of diagnostic dicts suitable for JSON serialization.
        """
        diagnostics = self._diagnostics_cache.get(uri, [])
        return [self._diagnostic_to_dict(d) for d in diagnostics]

    def get_all_snapshots(self) -> dict[str, list[dict[str, Any]]]:
        """Return snapshots for every tracked URI.

        Returns:
            Mapping of URI to its list of diagnostic dicts.
        """
        return {
            uri: [self._diagnostic_to_dict(d) for d in diags]
            for uri, diags in self._diagnostics_cache.items()
        }

    def snapshot_to_json(self, uri: str | None = None) -> str:
        """Render diagnostics as a JSON string.

        When *uri* is provided, returns a JSON array of diagnostics for that
        single document.  When *uri* is ``None``, returns a JSON object keyed
        by URI.

        Args:
            uri: Optional document URI to scope the snapshot.

        Returns:
            Deterministic JSON string.
        """
        if uri is not None:
            data: Any = self.get_diagnostics_snapshot(uri)
        else:
            data = self.get_all_snapshots()
        return json.dumps(data, indent=2, sort_keys=True)

    # ------------------------------------------------------------------
    # Block-level checks (unchanged)
    # ------------------------------------------------------------------

    def _check_required_blocks(
        self,
        blocks: list,
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check for required blocks.

        Args:
            blocks: Parsed blocks.
            diagnostics: List to append diagnostics to.
        """
        has_geometry = any(b.name == "geometry" for b in blocks)
        has_basis = any(b.name == "basis" for b in blocks)
        has_task = any(b.name == "task" for b in blocks)

        if not has_geometry:
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0), end=Position(line=0, character=0)
                    ),
                    message="Missing required 'geometry' block",
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-lsp",
                )
            )

        if not has_basis:
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0), end=Position(line=0, character=0)
                    ),
                    message="Missing required 'basis' block",
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-lsp",
                )
            )

        if not has_task:
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0), end=Position(line=0, character=0)
                    ),
                    message="Missing required 'task' directive",
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-lsp",
                )
            )

    def _check_block(
        self,
        block: NWchemSection,
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check a specific block for issues.

        Args:
            block: Parsed block.
            lines: Document lines.
            diagnostics: List to append diagnostics to.
        """
        if block.name == "basis":
            self._check_basis_block(block, lines, diagnostics)
        elif block.name == "dft":
            self._check_dft_block(block, lines, diagnostics)
        elif block.name == "task":
            self._check_task_block(block, lines, diagnostics)
        elif block.name == "scf":
            self._check_scf_block(block, lines, diagnostics)

    def _check_basis_block(
        self,
        block: NWchemSection,
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check basis block for issues.

        Args:
            block: Parsed block.
            lines: Document lines.
            diagnostics: List to append diagnostics to.
        """
        for i, line in enumerate(block.content, block.line_start + 1):
            stripped = line.strip().lower()

            # Check for library keyword
            if "library" in stripped:
                parts = stripped.split()
                if len(parts) >= 3 and parts[1] == "library":
                    basis_set = parts[2]
                    if basis_set not in self.VALID_BASIS_SETS:
                        # Warning for unknown basis set
                        start_col = line.lower().find(basis_set)
                        diagnostics.append(
                            Diagnostic(
                                range=Range(
                                    start=Position(line=i - 1, character=start_col),
                                    end=Position(line=i - 1, character=start_col + len(basis_set)),
                                ),
                                message=f"Unknown basis set: '{basis_set}'",
                                severity=DiagnosticSeverity.Warning,
                                source="nwchem-lsp",
                            )
                        )

    def _check_dft_block(
        self,
        block: NWchemSection,
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check DFT block for issues.

        Args:
            block: Parsed block.
            lines: Document lines.
            diagnostics: List to append diagnostics to.
        """
        for i, line in enumerate(block.content, block.line_start + 1):
            stripped = line.strip().lower()

            # Check xc functional
            if stripped.startswith("xc"):
                parts = stripped.split()
                if len(parts) >= 2:
                    functional = parts[1]
                    if functional not in self.VALID_XC_FUNCTIONALS:
                        start_col = line.lower().find(functional)
                        diagnostics.append(
                            Diagnostic(
                                range=Range(
                                    start=Position(line=i - 1, character=start_col),
                                    end=Position(line=i - 1, character=start_col + len(functional)),
                                ),
                                message=f"Unknown XC functional: '{functional}'",
                                severity=DiagnosticSeverity.Warning,
                                source="nwchem-lsp",
                            )
                        )

    def _check_task_block(
        self,
        block: NWchemSection,
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check task block for issues.

        Args:
            block: Parsed block.
            lines: Document lines.
            diagnostics: List to append diagnostics to.
        """
        # Task is a single line directive
        task_line = lines[block.line_start - 1].strip().lower()
        parts = task_line.split()

        if len(parts) >= 2:
            theory = parts[1]
            valid_theories = {"scf", "dft", "mp2", "ccsd", "ccsd(t)", "mcscf", "semi"}
            if theory not in valid_theories:
                start_col = lines[block.line_start - 1].lower().find(theory)
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=block.line_start - 1, character=start_col),
                            end=Position(
                                line=block.line_start - 1, character=start_col + len(theory)
                            ),
                        ),
                        message=f"Unknown theory level: '{theory}'",
                        severity=DiagnosticSeverity.Error,
                        source="nwchem-lsp",
                    )
                )

        if len(parts) >= 3:
            operation = parts[2]
            if operation not in self.VALID_TASK_OPERATIONS:
                start_col = lines[block.line_start - 1].lower().find(operation)
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=block.line_start - 1, character=start_col),
                            end=Position(
                                line=block.line_start - 1, character=start_col + len(operation)
                            ),
                        ),
                        message=f"Unknown task operation: '{operation}'",
                        severity=DiagnosticSeverity.Warning,
                        source="nwchem-lsp",
                    )
                )

    def _check_scf_block(
        self,
        block: NWchemSection,
        lines: list[str],
        diagnostics: list[Diagnostic],
    ) -> None:
        """Check SCF block for issues.

        Args:
            block: Parsed block.
            lines: Document lines.
            diagnostics: List to append diagnostics to.
        """
        for i, line in enumerate(block.content, block.line_start + 1):
            stripped = line.strip().lower()

            # Check maxiter
            if stripped.startswith("maxiter"):
                parts = stripped.split()
                if len(parts) >= 2:
                    try:
                        maxiter = int(parts[1])
                        if maxiter < 1 or maxiter > 1000:
                            start_col = line.lower().find(parts[1])
                            diagnostics.append(
                                Diagnostic(
                                    range=Range(
                                        start=Position(line=i - 1, character=start_col),
                                        end=Position(
                                            line=i - 1, character=start_col + len(parts[1])
                                        ),
                                    ),
                                    message=f"Unusual maxiter value: {maxiter}",
                                    severity=DiagnosticSeverity.Warning,
                                    source="nwchem-lsp",
                                )
                            )
                    except ValueError:
                        start_col = line.lower().find(parts[1])
                        diagnostics.append(
                            Diagnostic(
                                range=Range(
                                    start=Position(line=i - 1, character=start_col),
                                    end=Position(line=i - 1, character=start_col + len(parts[1])),
                                ),
                                message=f"Invalid maxiter value: '{parts[1]}'",
                                severity=DiagnosticSeverity.Error,
                                source="nwchem-lsp",
                            )
                        )


__all__ = ["DiagnosticProvider"]

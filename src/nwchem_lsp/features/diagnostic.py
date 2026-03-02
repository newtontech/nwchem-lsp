"""LSP diagnostic provider for NWChem."""

from __future__ import annotations

from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)
from pygls.server import LanguageServer

from ..data.keywords import ALL_KEYWORDS, get_keyword
from ..parser.nwchem_parser import NwchemParser as NWChemParser


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

    def get_diagnostics(self, text: str) -> list[Diagnostic]:
        """Get diagnostics for the document.

        Args:
            text: Document text.

        Returns:
            List of diagnostics.
        """
        diagnostics: list[Diagnostic] = []

        parser = NWChemParser(text)
        blocks = parser.parse()
        lines = text.split("\n")

        # Check for required blocks
        self._check_required_blocks(blocks, diagnostics)

        # Check each block
        for block in blocks:
            self._check_block(block, lines, diagnostics)

        return diagnostics

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
        block,
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
        block,
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
        block,
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
        block,
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
        block,
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

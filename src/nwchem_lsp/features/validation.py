"""Validation framework for NWChem input files.

Provides NWChemValidationProvider for detecting mutually exclusive parameters,
conflicting method sections, basis set issues, and charge/multiplicity warnings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)


@dataclass
class ValidationResult:
    """Represents a single validation result."""

    line: int
    character: int
    message: str
    severity: DiagnosticSeverity
    source: str = "nwchem-lsp"
    end_character: int = 0

    def to_diagnostic(self) -> Diagnostic:
        """Convert to LSP Diagnostic."""
        end_char = self.end_character if self.end_character else self.character + 1
        return Diagnostic(
            range=Range(
                start=Position(line=self.line, character=self.character),
                end=Position(line=self.line, character=end_char),
            ),
            message=self.message,
            severity=self.severity,
            source=self.source,
        )


# Mutually exclusive theory methods
# SCF and DFT should not both have task directives
METHOD_CONFLICTS: list[tuple[set[str], str]] = [
    ({"scf", "dft"}, "Both SCF and DFT sections detected — SCF and DFT are mutually exclusive methods"),
    ({"mp2", "ccsd"}, "Both MP2 and CCSD sections detected — choose one post-HF method"),
    ({"mp2", "ccsd(t)"}, "Both MP2 and CCSD(T) sections detected — CCSD(T) supersedes MP2"),
    ({"dft", "mp2"}, "Both DFT and MP2 sections detected — DFT and wavefunction methods are mutually exclusive"),
    ({"dft", "ccsd"}, "Both DFT and CCSD sections detected — DFT and coupled-cluster are mutually exclusive"),
    ({"scf", "dft", "mp2"}, "SCF, DFT, and MP2 sections all detected — choose a single method"),
    ({"scf", "dft", "ccsd"}, "SCF, DFT, and CCSD sections all detected — choose a single method"),
]

# Task theory vs section conflicts
# If task uses SCF but DFT section exists, or vice versa
TASK_SECTION_CONFLICTS: list[tuple[str, set[str], str]] = [
    ("scf", {"dft"}, "Task uses SCF theory but DFT section is present"),
    ("dft", {"scf"}, "Task uses DFT theory but SCF section is present"),
    ("mp2", {"dft"}, "Task uses MP2 theory but DFT section is present (DFT and wavefunction methods are incompatible)"),
    ("ccsd", {"dft"}, "Task uses CCSD theory but DFT section is present"),
    ("ccsd(t)", {"dft"}, "Task uses CCSD(T) theory but DFT section is present"),
]

# Charge/multiplicity warning patterns
CHARGE_WARNINGS: list[tuple[int, int, str]] = [
    # (charge, multiplicity, warning message)
    (0, 1, "Charge 0 with multiplicity 1 — this is a singlet neutral, verify this is intended"),
    (1, 1, "Charge +1 with multiplicity 1 — verify cationic singlet is intended"),
    (-1, 1, "Charge -1 with multiplicity 1 — verify anionic singlet is intended"),
    (0, 2, "Charge 0 with multiplicity 2 — this is a doublet radical, verify this is intended"),
    (0, 3, "Charge 0 with multiplicity 3 — this is a triplet state, verify this is intended"),
]


class NWChemValidationProvider:
    """Validates NWChem input files for configuration conflicts.

    Checks for:
    - Task conflicts (duplicate tasks, method conflicts)
    - Method section conflicts (SCF vs DFT, MP2 vs CCSD)
    - Basis set issues (duplicate definitions)
    - Charge/multiplicity warnings
    """

    def __init__(self) -> None:
        """Initialize the validation provider."""

    def validate(self, text: str, sections: dict[str, list[Any]]) -> list[ValidationResult]:
        """Run all validation checks on parsed NWChem content.

        Args:
            text: The full NWChem input text.
            sections: Dictionary of parsed sections from NwchemParser.

        Returns:
            List of validation results.
        """
        results: list[ValidationResult] = []

        lines = text.split("\n")

        results.extend(self._check_task_conflicts(lines, sections))
        results.extend(self._check_method_conflicts(lines, sections))
        results.extend(self._check_basis_set_issues(lines, sections))
        results.extend(self._check_charge_multiplicity(lines, sections))

        return results

    def validate_to_diagnostics(
        self, text: str, sections: dict[str, list[Any]]
    ) -> list[Diagnostic]:
        """Run validation and convert results to LSP diagnostics.

        Args:
            text: The full NWChem input text.
            sections: Dictionary of parsed sections from NwchemParser.

        Returns:
            List of LSP Diagnostic objects.
        """
        results = self.validate(text, sections)
        return [r.to_diagnostic() for r in results]

    def _check_task_conflicts(
        self, lines: list[str], sections: dict[str, list[Any]]
    ) -> list[ValidationResult]:
        """Check for task-related conflicts.

        Detects:
        - Duplicate task directives
        - Task theory vs section conflicts
        """
        results: list[ValidationResult] = []

        # Find all task lines
        task_lines: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if stripped.startswith("task ") and not stripped.startswith("#"):
                task_lines.append((i, stripped))

        # Check for duplicate tasks
        if len(task_lines) > 1:
            for line_num, task_line in task_lines[1:]:
                col = line.lower().find("task")
                results.append(
                    ValidationResult(
                        line=line_num,
                        character=col if col >= 0 else 0,
                        message="Duplicate task directive — NWChem uses the last task directive",
                        severity=DiagnosticSeverity.Warning,
                        end_character=col + 4 if col >= 0 else 4,
                    )
                )

        # Check task theory vs section conflicts
        for line_num, task_line in task_lines:
            parts = task_line.split()
            if len(parts) >= 2:
                task_theory = parts[1]
                for theory, conflicting_sections, message in TASK_SECTION_CONFLICTS:
                    if task_theory == theory:
                        present_sections = set(sections.keys())
                        if conflicting_sections & present_sections:
                            conflict_section = conflicting_sections.pop()
                            if conflict_section in sections:
                                section_obj = sections[conflict_section][0]
                                section_line = section_obj.start_line
                                results.append(
                                    ValidationResult(
                                        line=section_line,
                                        character=0,
                                        message=message,
                                        severity=DiagnosticSeverity.Warning,
                                    )
                                )

        return results

    def _check_method_conflicts(
        self, lines: list[str], sections: dict[str, list[Any]]
    ) -> list[ValidationResult]:
        """Check for mutually exclusive method sections.

        Detects:
        - SCF and DFT sections both present
        - MP2 and CCSD sections both present
        - Other incompatible method combinations
        """
        results: list[ValidationResult] = []

        present_sections = set(sections.keys())

        for section_set, message in METHOD_CONFLICTS:
            if section_set <= present_sections:
                # Find the line of the second conflicting section and report there
                for section_name in sorted(section_set):
                    if section_name in sections:
                        section_obj = sections[section_name][0]
                        section_line = section_obj.start_line
                        results.append(
                            ValidationResult(
                                line=section_line,
                                character=0,
                                message=message,
                                severity=DiagnosticSeverity.Warning,
                            )
                        )
                        break  # Report once per conflict set

        return results

    def _check_basis_set_issues(
        self, lines: list[str], sections: dict[str, list[Any]]
    ) -> list[ValidationResult]:
        """Check for basis set issues.

        Detects:
        - Duplicate basis set definitions for the same element
        - Basis sections without library keyword
        """
        results: list[ValidationResult] = []

        if "basis" not in sections:
            return results

        # Track basis definitions per element
        element_basis: dict[str, list[tuple[int, str]]] = {}

        for basis_section in sections["basis"]:
            for i, line in enumerate(basis_section.content):
                stripped = line.strip().lower()
                if not stripped or stripped == "end" or stripped.startswith("#"):
                    continue

                parts = stripped.split()
                if len(parts) >= 3 and parts[1] == "library":
                    element = parts[0]
                    basis_set = parts[2]
                    if element not in element_basis:
                        element_basis[element] = []
                    element_basis[element].append(
                        (basis_section.start_line + i, basis_set)
                    )

        # Check for duplicate basis definitions
        for element, definitions in element_basis.items():
            if len(definitions) > 1:
                for line_num, basis_set in definitions[1:]:
                    col = lines[line_num].lower().find(basis_set) if line_num < len(lines) else 0
                    results.append(
                        ValidationResult(
                            line=line_num,
                            character=col if col >= 0 else 0,
                            message=f"Duplicate basis definition for element '{element}' — "
                            f"previous definition used",
                            severity=DiagnosticSeverity.Warning,
                            end_character=col + len(basis_set) if col >= 0 else len(basis_set),
                        )
                    )

        return results

    def _check_charge_multiplicity(
        self, lines: list[str], sections: dict[str, list[Any]]
    ) -> list[ValidationResult]:
        """Check for charge/multiplicity warnings.

        Detects:
        - Unusual charge/multiplicity combinations
        - Multiple charge directives
        """
        results: list[ValidationResult] = []

        # Find all charge directives
        charge_lines: list[tuple[int, int]] = []
        charge_line_num: int | None = None
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if stripped.startswith("charge ") and not stripped.startswith("#"):
                parts = stripped.split()
                if len(parts) >= 2:
                    try:
                        charge = int(parts[1])
                        charge_lines.append((i, charge))
                        if charge_line_num is None:
                            charge_line_num = i
                    except ValueError:
                        pass

        # Check for multiple charge directives
        if len(charge_lines) > 1:
            for line_num, _ in charge_lines[1:]:
                col = lines[line_num].lower().find("charge") if line_num < len(lines) else 0
                results.append(
                    ValidationResult(
                        line=line_num,
                        character=col if col >= 0 else 0,
                        message="Multiple charge directives — last charge value will be used",
                        severity=DiagnosticSeverity.Warning,
                        end_character=col + 6 if col >= 0 else 6,
                    )
                )

        # Check charge/multiplicity combinations
        # Look for multiplicity in SCF or DFT sections
        multiplicity: int | None = None
        for section_name in ("scf", "dft"):
            if section_name in sections:
                for section_obj in sections[section_name]:
                    for line in section_obj.content:
                        stripped = line.strip().lower()
                        if stripped.startswith("mult") or stripped.startswith("multiplicity"):
                            parts = stripped.split()
                            if len(parts) >= 2:
                                try:
                                    multiplicity = int(parts[1])
                                except ValueError:
                                    pass

        if charge_lines and multiplicity is not None:
            charge = charge_lines[-1][1]
            for expected_charge, expected_mult, warning_msg in CHARGE_WARNINGS:
                if charge == expected_charge and multiplicity == expected_mult:
                    charge_line = charge_lines[-1][0]
                    col = lines[charge_line].lower().find("charge") if charge_line < len(lines) else 0
                    results.append(
                        ValidationResult(
                            line=charge_line,
                            character=col if col >= 0 else 0,
                            message=warning_msg,
                            severity=DiagnosticSeverity.Information,
                            end_character=col + 6 if col >= 0 else 6,
                        )
                    )
                    break  # Only report first matching warning

        return results


__all__ = ["NWChemValidationProvider", "ValidationResult"]

"""LSP diagnostic provider for NWChem."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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

logger = logging.getLogger(__name__)

# Mapping from DiagnosticSeverity enum to human-readable strings.
_SEVERITY_NAMES: dict[int, str] = {
    DiagnosticSeverity.Error: "error",
    DiagnosticSeverity.Warning: "warning",
    DiagnosticSeverity.Information: "information",
    DiagnosticSeverity.Hint: "hint",
}

RULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "NW000": {
        "description": "Catch-all / generic diagnostic",
        "severity": "warning",
        "blocking": False,
        "source_provenance": "",
        "version_scope": None,
    },
    "NW001": {
        "description": "Unknown theory level in task directive",
        "severity": "error",
        "blocking": True,
        "source_provenance": "https://nwchemgit.github.io/Task.html",
        "version_scope": None,
    },
    "NW002": {
        "description": "Missing required block (geometry, basis, or task)",
        "severity": "error",
        "blocking": True,
        "source_provenance": "https://nwchemgit.github.io/Input.html",
        "version_scope": None,
    },
    "NW003": {
        "description": "Unknown basis set in library reference",
        "severity": "warning",
        "blocking": False,
        "source_provenance": "https://nwchemgit.github.io/Basis.html",
        "version_scope": None,
    },
    "NW004": {
        "description": "Unknown task operation",
        "severity": "warning",
        "blocking": False,
        "source_provenance": "https://nwchemgit.github.io/Task.html",
        "version_scope": None,
    },
    "NW005": {
        "description": "Unknown DFT XC functional",
        "severity": "warning",
        "blocking": False,
        "source_provenance": "https://nwchemgit.github.io/DFT.html",
        "version_scope": None,
    },
    "NW006": {
        "description": "Unusual SCF maxiter value",
        "severity": "warning",
        "blocking": False,
        "source_provenance": "https://nwchemgit.github.io/SCF.html",
        "version_scope": None,
    },
    "NW007": {
        "description": "Invalid maxiter value (non-integer)",
        "severity": "error",
        "blocking": True,
        "source_provenance": "https://nwchemgit.github.io/SCF.html",
        "version_scope": None,
    },
    "NW008": {
        "description": "Unexpected 'end' keyword with no matching section",
        "severity": "error",
        "blocking": True,
        "source_provenance": "https://nwchemgit.github.io/Input.html",
        "version_scope": None,
    },
    "NW009": {
        "description": "Unclosed section block",
        "severity": "error",
        "blocking": True,
        "source_provenance": "https://nwchemgit.github.io/Input.html",
        "version_scope": None,
    },
}


@dataclass
class FixPreview:

    rule_id: str
    description: str
    action: str
    range: Optional[Dict[str, Any]] = None
    replacement: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "rule_id": self.rule_id,
            "description": self.description,
            "action": self.action,
        }
        if self.range is not None:
            result["range"] = self.range
        if self.replacement is not None:
            result["replacement"] = self.replacement
        if self.alternatives:
            result["alternatives"] = list(self.alternatives)
        return result


@dataclass
class DiagnosticEnvelope:
    """DiagnosticEnvelope/v1 — agent-compatible diagnostic wrapper.

    Extends the standard LSP Diagnostic with metadata required by agent CLI
    and OpenQC gates: rule ID, blocking flag, source provenance, and version
    scope.
    """

    range: Dict[str, Any]
    message: str
    severity: int
    severity_label: str
    source: str
    code: Optional[str]
    rule_id: str
    blocking: bool
    source_provenance: str
    version_scope: Optional[str]
    fix_preview: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        result: Dict[str, Any] = {
            "range": self.range,
            "message": self.message,
            "severity": self.severity,
            "severity_label": self.severity_label,
            "source": self.source,
            "code": self.code,
            "rule_id": self.rule_id,
            "blocking": self.blocking,
            "source_provenance": self.source_provenance,
            "version_scope": self.version_scope,
        }
        if self.fix_preview is not None:
            result["fix_preview"] = self.fix_preview
        return result


class NwchemDiagnosticProvider:
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
        self.server = server
        # Per-URI cache of the most recent diagnostics, used for snapshots.
        self._diagnostics_cache: dict[str, list[Diagnostic]] = {}

    def get_diagnostics(self, text: str) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        try:
            parser = NWChemParser(text)
            blocks = parser.parse()
        except (ParseError, ValidationError) as exc:
            logger.warning("Parse/validation error in diagnostics: %s", exc)
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
            logger.exception("Unexpected error during parsing in diagnostics")
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

        # Check each block
        for block in blocks:
            try:
                self._check_block(block, lines, diagnostics)
            except Exception:
                logger.exception(
                    "Error checking block '%s' starting at line %d",
                    getattr(block, "name", "<unknown>"),
                    getattr(block, "start_line", -1),
                )

        return diagnostics

    def update_cache(self, uri: str, diagnostics: list[Diagnostic]) -> None:
        self._diagnostics_cache[uri] = list(diagnostics)

    # ------------------------------------------------------------------
    # Snapshot / Envelope API
    # ------------------------------------------------------------------

    @staticmethod
    def _assign_rule_id(message: str) -> str:
        msg_lower = message.lower()
        if "unknown theory level" in msg_lower:
            return "NW001"
        if "missing required" in msg_lower and "geometry" in msg_lower:
            return "NW002"
        if "missing required" in msg_lower and "basis" in msg_lower:
            return "NW002"
        if "missing required" in msg_lower and "task" in msg_lower:
            return "NW002"
        if "unknown basis set" in msg_lower:
            return "NW003"
        if "unknown task operation" in msg_lower:
            return "NW004"
        if "unknown xc functional" in msg_lower:
            return "NW005"
        if "unusual maxiter" in msg_lower:
            return "NW006"
        if "invalid maxiter" in msg_lower:
            return "NW007"
        if "unexpected 'end'" in msg_lower:
            return "NW008"
        if "unclosed section" in msg_lower:
            return "NW009"
        return "NW000"

    @staticmethod
    def _is_blocking(rule_id: str) -> bool:
        meta = RULE_REGISTRY.get(rule_id)
        if meta is not None:
            return meta.get("blocking", False)
        return rule_id in {"NW001", "NW002", "NW007", "NW008", "NW009"}

    @staticmethod
    def _get_source_provenance(rule_id: str) -> str:
        meta = RULE_REGISTRY.get(rule_id)
        if meta is not None:
            return meta.get("source_provenance", "")
        return ""

    @staticmethod
    def _get_version_scope(rule_id: str) -> Optional[str]:
        meta = RULE_REGISTRY.get(rule_id)
        if meta is not None:
            return meta.get("version_scope")
        return None

    def _diagnostic_to_dict(self, diag: Diagnostic) -> dict[str, Any]:
        severity_value = diag.severity if diag.severity is not None else DiagnosticSeverity.Error
        rule_id = self._assign_rule_id(diag.message)
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
            "rule_id": rule_id,
            "blocking": self._is_blocking(rule_id),
            "source_provenance": self._get_source_provenance(rule_id),
            "version_scope": self._get_version_scope(rule_id),
        }

    def to_envelope(self, diag: Diagnostic) -> DiagnosticEnvelope:
        severity_value = diag.severity if diag.severity is not None else DiagnosticSeverity.Error
        rule_id = self._assign_rule_id(diag.message)
        range_dict = {
            "start": {
                "line": diag.range.start.line,
                "character": diag.range.start.character,
            },
            "end": {
                "line": diag.range.end.line,
                "character": diag.range.end.character,
            },
        }
        fix = self.generate_fix_preview(diag, rule_id)
        return DiagnosticEnvelope(
            range=range_dict,
            message=diag.message,
            severity=severity_value,
            severity_label=_SEVERITY_NAMES.get(severity_value, "unknown"),
            source=diag.source or "nwchem-lsp",
            code=str(diag.code) if diag.code is not None else None,
            rule_id=rule_id,
            blocking=self._is_blocking(rule_id),
            source_provenance=self._get_source_provenance(rule_id),
            version_scope=self._get_version_scope(rule_id),
            fix_preview=fix.to_dict() if fix is not None else None,
        )

    @staticmethod
    def generate_fix_preview(
        diag: Diagnostic, rule_id: str
    ) -> Optional[FixPreview]:
        msg = diag.message
        rng = {
            "start": {"line": diag.range.start.line, "character": diag.range.start.character},
            "end": {"line": diag.range.end.line, "character": diag.range.end.character},
        }

        if rule_id == "NW001":
            return FixPreview(
                rule_id=rule_id,
                description="Replace unknown theory with a valid theory (scf, dft, mp2, ccsd, mcscf, semi)",
                action="replace",
                range=rng,
                replacement="scf",
                alternatives=["scf", "dft", "mp2", "ccsd", "mcscf", "semi"],
            )
        if rule_id == "NW002":
            if "geometry" in msg.lower():
                return FixPreview(
                    rule_id=rule_id,
                    description="Insert a minimal geometry block at the top of the file",
                    action="insert",
                    range={"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                    replacement="geometry\n  H 0.0 0.0 0.0\nend\n\n",
                )
            if "basis" in msg.lower():
                return FixPreview(
                    rule_id=rule_id,
                    description="Insert a minimal basis block",
                    action="insert",
                    range={"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                    replacement="basis\n  H library sto-3g\nend\n\n",
                )
            if "task" in msg.lower():
                return FixPreview(
                    rule_id=rule_id,
                    description="Insert a task directive at the end of the file",
                    action="insert",
                    range={"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                    replacement="task scf energy\n",
                )
        if rule_id == "NW003":
            return FixPreview(
                rule_id=rule_id,
                description="Replace unknown basis set with a common alternative",
                action="replace",
                range=rng,
                replacement="sto-3g",
                alternatives=["sto-3g", "3-21g", "6-31g", "cc-pvdz", "def2-svp"],
            )
        if rule_id == "NW004":
            return FixPreview(
                rule_id=rule_id,
                description="Replace unknown task operation with a valid operation",
                action="replace",
                range=rng,
                replacement="energy",
                alternatives=["energy", "optimize", "frequencies", "gradient", "hessian"],
            )
        if rule_id == "NW005":
            return FixPreview(
                rule_id=rule_id,
                description="Replace unknown XC functional with a common functional",
                action="replace",
                range=rng,
                replacement="b3lyp",
                alternatives=["b3lyp", "pbe", "pbe0", "m06-2x", "wb97x-d", "cam-b3lyp"],
            )
        if rule_id == "NW006":
            return FixPreview(
                rule_id=rule_id,
                description="Adjust maxiter to a typical value (100)",
                action="replace",
                range=rng,
                replacement="100",
            )
        if rule_id == "NW007":
            return FixPreview(
                rule_id=rule_id,
                description="Replace non-integer maxiter with a valid integer",
                action="replace",
                range=rng,
                replacement="100",
            )
        return None

    def get_diagnostics_snapshot(self, uri: str) -> list[dict[str, Any]]:
        diagnostics = self._diagnostics_cache.get(uri, [])
        return [self._diagnostic_to_dict(d) for d in diagnostics]

    def get_all_snapshots(self) -> dict[str, list[dict[str, Any]]]:
        return {
            uri: [self._diagnostic_to_dict(d) for d in diags]
            for uri, diags in self._diagnostics_cache.items()
        }

    def snapshot_to_json(self, uri: str | None = None) -> str:
        if uri is not None:
            data: Any = self.get_diagnostics_snapshot(uri)
        else:
            data = self.get_all_snapshots()
        return json.dumps(data, indent=2, sort_keys=True)

    # ------------------------------------------------------------------
    # Block-level checks
    # ------------------------------------------------------------------

    def _check_required_blocks(
        self,
        blocks: list,
        diagnostics: list[Diagnostic],
    ) -> None:
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


__all__ = ["NwchemDiagnosticProvider"]

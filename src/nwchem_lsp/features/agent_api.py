"""Machine-readable code-intelligence API for AI coding agents.

Provides structured JSON endpoints for Claude Code, OpenCode, Codex,
and other agent workflows. Endpoints expose diagnostics, symbols,
hover information, and document structure without requiring LSP protocol.

Capability issues implemented:

- #65: ``describe_domain_language()`` -- NWChem input language description
- #66: ``lookup_section()``, ``lookup_keyword()`` -- schema lookup
- #67: ``get_examples()``, ``next_token_suggestions()`` -- examples and guidance
- #74: ``parse_log()``, ``parse_nwchem_output()`` -- output/log diagnostics
- #84: ``get_rule_manifest()``, ``openqc_smoke()`` -- OpenQC smoke test
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..data.keywords import (
    ALL_KEYWORDS,
    BASIS_SETS,
    DFT_FUNCTIONALS,
    ELEMENTS,
    TASK_OPERATIONS,
    TASK_THEORIES,
    TOP_LEVEL_SECTIONS,
)
from .diagnostic import DiagnosticProvider
from .lint import NwchemLintProvider, RULE_DESCRIPTIONS


# ------------------------------------------------------------------
# NWChem domain language description (#65)
# ------------------------------------------------------------------

_DOMAIN_LANGUAGE_DESCRIPTION: Dict[str, Any] = {
    "language": "nwchem",
    "file_extensions": [".nw", ".nwchem"],
    "description": (
        "NWChem input format for computational chemistry. Files consist of "
        "top-level directives (title, charge, memory, etc.) and block "
        "sections (geometry, basis, scf, dft, mp2, ccds, etc.) delimited "
        "by END keywords. Task directives specify the calculation type."
    ),
    "sections": [
        {
            "name": "geometry",
            "required": True,
            "description": "Molecular geometry specification with atom coordinates",
            "keywords": ["units", "angstroms", "bohr", "autosym", "noautoz"],
        },
        {
            "name": "basis",
            "required": True,
            "description": "Basis set specification per element",
            "keywords": ["spherical", "cartesian", "library", "file"],
        },
        {
            "name": "scf",
            "required": False,
            "description": "Self-Consistent Field (Hartree-Fock) options",
            "keywords": ["singlet", "doublet", "triplet", "rhf", "uhf", "rohf",
                         "maxiter", "thresh", "direct", "semidirect"],
        },
        {
            "name": "dft",
            "required": False,
            "description": "Density Functional Theory options",
            "keywords": ["xc", "grid", "convergence", "iterations", "direct",
                         "noio", "odft", "cdft", "mult"],
        },
        {
            "name": "mp2",
            "required": False,
            "description": "Second-order perturbation theory options",
            "keywords": ["tight", "freeze", "ri", "cd"],
        },
        {
            "name": "ccsd",
            "required": False,
            "description": "Coupled Cluster Singles and Doubles options",
            "keywords": ["tce", "freeze", "thresh", "maxiter"],
        },
        {
            "name": "tce",
            "required": False,
            "description": "Tensor Contraction Engine options",
            "keywords": ["freeze", "thresh", "maxiter"],
        },
    ],
    "task_directives": {
        "syntax": "task <theory> <operation>",
        "theories": sorted(TASK_THEORIES),
        "operations": sorted(TASK_OPERATIONS),
    },
    "common_functionals": sorted(DFT_FUNCTIONALS)[:20],
    "common_basis_sets": sorted(BASIS_SETS)[:20],
}

# ------------------------------------------------------------------
# NWChem input examples (#67)
# ------------------------------------------------------------------

_NWCHEM_EXAMPLES: List[Dict[str, str]] = [
    {
        "name": "HF single-point energy",
        "source": (
            'title "Water HF energy"\n'
            "geometry units angstroms\n"
            "  O  0.0  0.0  0.0\n"
            "  H  0.0  0.8  0.6\n"
            "  H  0.0 -0.8  0.6\n"
            "end\n"
            "\n"
            "basis\n"
            "  * library 6-31g*\n"
            "end\n"
            "\n"
            "task scf energy\n"
        ),
    },
    {
        "name": "DFT geometry optimization",
        "source": (
            'title "Water DFT optimization"\n'
            "geometry units angstroms\n"
            "  O  0.0  0.0  0.0\n"
            "  H  0.0  0.8  0.6\n"
            "  H  0.0 -0.8  0.6\n"
            "end\n"
            "\n"
            "basis\n"
            "  * library cc-pvdz\n"
            "end\n"
            "\n"
            "dft\n"
            "  xc b3lyp\n"
            "  grid fine\n"
            "end\n"
            "\n"
            "task dft optimize\n"
        ),
    },
    {
        "name": "MP2 correlation energy",
        "source": (
            'title "Water MP2"\n'
            "geometry units angstroms\n"
            "  O  0.0  0.0  0.0\n"
            "  H  0.0  0.8  0.6\n"
            "  H  0.0 -0.8  0.6\n"
            "end\n"
            "\n"
            "basis\n"
            "  * library aug-cc-pvdz\n"
            "end\n"
            "\n"
            "mp2\n"
            "  freeze atomic\n"
            "end\n"
            "\n"
            "task mp2 energy\n"
        ),
    },
    {
        "name": "CCSD(T) single-point",
        "source": (
            'title "Water CCSD(T)"\n'
            "geometry units angstroms\n"
            "  O  0.0  0.0  0.0\n"
            "  H  0.0  0.8  0.6\n"
            "  H  0.0 -0.8  0.6\n"
            "end\n"
            "\n"
            "basis\n"
            "  * library cc-pvtz\n"
            "end\n"
            "\n"
            "ccsd\n"
            "  freeze atomic\n"
            "  thresh 1e-6\n"
            "end\n"
            "\n"
            "task ccsd energy\n"
        ),
    },
]

# ------------------------------------------------------------------
# Log output pattern matchers for parse_log (#74)
# ------------------------------------------------------------------

_LOG_PATTERNS: List[Dict[str, Any]] = [
    {
        "pattern": r"SCF failed to converge",
        "code": "NWCHEM-E044",
        "severity": "error",
        "message": "SCF calculation did not converge within iteration limit",
    },
    {
        "pattern": r"RuntimeError|FATAL ERROR|Aborting",
        "code": "NWCHEM-E044",
        "severity": "error",
        "message": "NWChem runtime error detected",
    },
    {
        "pattern": r"Insufficient memory",
        "code": "NWCHEM-E044",
        "severity": "error",
        "message": "Insufficient memory for calculation",
    },
    {
        "pattern": r"could not find basis set",
        "code": "NWCHEM-E044",
        "severity": "error",
        "message": "Basis set not found in library",
    },
    {
        "pattern": r"ga_exit\b|djrfATAL|general error",
        "code": "NWCHEM-E044",
        "severity": "error",
        "message": "Global Arrays / NWChem internal error",
    },
    {
        "pattern": r"Total SCF energy\s*=\s*([-\d.E+]+)",
        "code": "NWCHEM-INFO-001",
        "severity": "info",
        "message": "SCF energy",
        "extract": True,
    },
    {
        "pattern": r"Total DFT energy\s*=\s*([-\d.E+]+)",
        "code": "NWCHEM-INFO-002",
        "severity": "info",
        "message": "DFT energy",
        "extract": True,
    },
    {
        "pattern": r"Optimization converged",
        "code": "NWCHEM-INFO-003",
        "severity": "info",
        "message": "Geometry optimization converged",
    },
    {
        "pattern": r"SCF.converged\s*=\s*TRUE",
        "code": "NWCHEM-INFO-004",
        "severity": "info",
        "message": "SCF converged",
    },
]


@dataclass
class AgentAPISnapshot:
    """Structured snapshot of code intelligence for a document."""

    uri: str = ""
    version: Optional[int] = None
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    outline: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "uri": self.uri,
                "version": self.version,
                "diagnostics": self.diagnostics,
                "symbols": self.symbols,
                "outline": self.outline,
                "metadata": self.metadata,
            },
            indent=2,
        )


class AgentAPIProvider:
    """Provides machine-readable code intelligence for AI agents.

    Capability methods:

    - :meth:`describe_domain_language` (#65)
    - :meth:`lookup_section`, :meth:`lookup_keyword` (#66)
    - :meth:`get_examples`, :meth:`next_token_suggestions` (#67)
    - :meth:`parse_log`, :meth:`parse_nwchem_output` (#74)
    - :meth:`get_rule_manifest`, :meth:`openqc_smoke` (#84)
    """

    def __init__(
        self,
        diagnostic_provider: Optional[DiagnosticProvider] = None,
        lint_provider: Optional[NwchemLintProvider] = None,
    ) -> None:
        self._diagnostic = diagnostic_provider
        self._lint = lint_provider

    # ------------------------------------------------------------------
    # Existing snapshot API
    # ------------------------------------------------------------------

    def get_snapshot(
        self,
        source: str,
        uri: str = "",
        version: Optional[int] = None,
    ) -> AgentAPISnapshot:
        """Return a comprehensive code-intelligence snapshot."""
        diagnostics: List[Dict[str, Any]] = []
        symbols: List[Dict[str, Any]] = []
        outline: List[Dict[str, Any]] = []

        # Collect diagnostics from all providers
        if self._diagnostic:
            diags = self._diagnostic.get_diagnostics(source)
            diagnostics.extend(
                {
                    "line": d.range.start.line,
                    "character": d.range.start.character,
                    "severity": d.severity,
                    "message": d.message,
                    "code": d.code,
                    "source": d.source,
                }
                for d in diags
            )

        if self._lint:
            lint_diags = self._lint.check(source)
            diagnostics.extend(
                {
                    "line": d.range.start.line,
                    "character": d.range.start.character,
                    "severity": d.severity,
                    "message": d.message,
                    "code": d.code,
                    "source": d.source,
                }
                for d in lint_diags
            )

        # Build outline from sections
        lines = source.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            if stripped.startswith("title ") or stripped == "title":
                outline.append({"type": "title", "line": i, "text": stripped})
            elif stripped.startswith("start "):
                outline.append(
                    {
                        "type": "module_start",
                        "line": i,
                        "name": (
                            stripped.split()[1] if len(stripped.split()) > 1 else ""
                        ),
                    }
                )
            elif stripped.startswith("task "):
                outline.append({"type": "task", "line": i, "text": stripped})
            elif not stripped.startswith("end") and (
                stripped
                in ("geometry", "basis", "scf", "dft", "mp2", "ccsd", "tce")
                or stripped.startswith("geometry ")
                or stripped.startswith("basis ")
            ):
                outline.append(
                    {"type": "section", "line": i, "name": stripped.split()[0]}
                )

        return AgentAPISnapshot(
            uri=uri,
            version=version,
            diagnostics=diagnostics,
            symbols=symbols,
            outline=outline,
            metadata={
                "language": "nwchem",
                "provider": "nwchem-lsp",
                "feature_count": {
                    "diagnostics": len(diagnostics),
                    "outline_items": len(outline),
                },
            },
        )

    def get_diagnostics_json(self, source: str, uri: str = "") -> str:
        """Return only diagnostics as JSON."""
        snapshot = self.get_snapshot(source, uri)
        return json.dumps(
            {
                "uri": snapshot.uri,
                "diagnostics": snapshot.diagnostics,
                "count": len(snapshot.diagnostics),
            },
            indent=2,
        )

    def get_outline_json(self, source: str, uri: str = "") -> str:
        """Return document outline as JSON."""
        snapshot = self.get_snapshot(source, uri)
        return json.dumps(
            {
                "uri": snapshot.uri,
                "outline": snapshot.outline,
            },
            indent=2,
        )

    # ------------------------------------------------------------------
    # Capability #65: Domain language description
    # ------------------------------------------------------------------

    @staticmethod
    def describe_domain_language() -> Dict[str, Any]:
        """Return a structured description of the NWChem input language.

        The description covers file extensions, sections, keywords,
        task directive syntax, common functionals and basis sets.

        Returns:
            Dictionary with full NWChem language schema.
        """
        return _DOMAIN_LANGUAGE_DESCRIPTION.copy()

    # ------------------------------------------------------------------
    # Capability #66: Schema lookup
    # ------------------------------------------------------------------

    @staticmethod
    def lookup_section(name: str) -> Optional[Dict[str, Any]]:
        """Look up a section by name.

        Args:
            name: Section name (case-insensitive).

        Returns:
            Dictionary with section metadata or None if not found.
        """
        key = name.lower()
        for section_info in _DOMAIN_LANGUAGE_DESCRIPTION["sections"]:
            if section_info["name"] == key:
                return {
                    "name": section_info["name"],
                    "required": section_info["required"],
                    "description": section_info["description"],
                    "keywords": section_info["keywords"],
                }
        # Also check top-level keywords
        from ..data.keywords import TOP_LEVEL_KEYWORDS

        kw_info = TOP_LEVEL_KEYWORDS.get(key)
        if kw_info:
            return {
                "name": kw_info.name,
                "required": kw_info.required,
                "description": kw_info.description,
                "keywords": kw_info.arguments or [],
            }
        return None

    @staticmethod
    def lookup_keyword(section: str, keyword: str) -> Optional[Dict[str, Any]]:
        """Look up a keyword within a section.

        Args:
            section: Section name (case-insensitive).
            keyword: Keyword name (case-insensitive).

        Returns:
            Dictionary with keyword metadata or None if not found.
        """
        from ..data.keywords import get_keyword_info, KeywordInfo

        info: Optional[KeywordInfo] = get_keyword_info(keyword.lower(), section.lower())
        if info is None:
            return None
        return {
            "name": info.name,
            "section": info.section,
            "description": info.description,
            "required": info.required,
            "arguments": info.arguments or [],
            "example": info.example,
            "deprecated": info.deprecated,
        }

    # ------------------------------------------------------------------
    # Capability #67: Examples and token suggestions
    # ------------------------------------------------------------------

    @staticmethod
    def get_examples() -> List[Dict[str, str]]:
        """Return curated NWChem input file examples.

        Returns:
            List of example dicts, each with ``name`` and ``source``.
        """
        return [ex.copy() for ex in _NWCHEM_EXAMPLES]

    @staticmethod
    def next_token_suggestions(
        context: str,
        prefix: str = "",
    ) -> List[Dict[str, str]]:
        """Suggest the next tokens given a parsing context.

        Args:
            context: Current context indicator. One of
                ``"top_level"``, ``"task_theory"``, ``"task_operation"``,
                ``"basis_set"``, ``"dft_functional"``, or a section name.
            prefix: Optional prefix to filter suggestions.

        Returns:
            List of suggestion dicts with ``text`` and ``description``.
        """
        suggestions: List[Dict[str, str]] = []
        prefix_lower = prefix.lower()

        if context == "top_level":
            for sec in TOP_LEVEL_SECTIONS:
                if sec.startswith(prefix_lower):
                    suggestions.append(
                        {"text": sec, "description": f"Section: {sec}"}
                    )
            suggestions.append(
                {"text": "task", "description": "Execute a computational task"}
            )
            suggestions.append(
                {"text": "title", "description": "Set calculation title"}
            )
            suggestions.append(
                {"text": "charge", "description": "Set molecular charge"}
            )
            suggestions.append(
                {"text": "memory", "description": "Set memory limits"}
            )

        elif context == "task_theory":
            for theory in sorted(TASK_THEORIES):
                if theory.startswith(prefix_lower):
                    suggestions.append(
                        {"text": theory, "description": f"Theory: {theory}"}
                    )

        elif context == "task_operation":
            for op in sorted(TASK_OPERATIONS):
                if op.startswith(prefix_lower):
                    suggestions.append(
                        {"text": op, "description": f"Operation: {op}"}
                    )

        elif context == "basis_set":
            for bs in sorted(BASIS_SETS):
                if bs.lower().startswith(prefix_lower):
                    suggestions.append(
                        {"text": bs, "description": f"Basis set: {bs}"}
                    )

        elif context == "dft_functional":
            for func in sorted(DFT_FUNCTIONALS):
                if func.lower().startswith(prefix_lower):
                    suggestions.append(
                        {"text": func, "description": f"Functional: {func}"}
                    )

        else:
            # Section-specific keyword suggestions
            section_key = context.lower()
            section_dict = ALL_KEYWORDS.get(section_key, {})
            for kw_name, kw_info in section_dict.items():
                if kw_name.startswith(prefix_lower):
                    suggestions.append(
                        {"text": kw_name, "description": kw_info.description}
                    )

        return suggestions

    # ------------------------------------------------------------------
    # Capability #74: Log / output parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_log(text: str) -> List[Dict[str, Any]]:
        """Parse NWChem log/output text for errors and key information.

        Args:
            text: Raw NWChem output/log file content.

        Returns:
            List of finding dicts with ``line``, ``code``, ``severity``,
            ``message``, and optionally ``value``.
        """
        findings: List[Dict[str, Any]] = []
        lines = text.splitlines()

        for line_num, line in enumerate(lines):
            for entry in _LOG_PATTERNS:
                match = re.search(entry["pattern"], line, re.IGNORECASE)
                if match:
                    finding: Dict[str, Any] = {
                        "line": line_num,
                        "code": entry["code"],
                        "severity": entry["severity"],
                        "message": entry["message"],
                    }
                    if entry.get("extract") and match.lastindex:
                        finding["value"] = match.group(1)
                    findings.append(finding)

        return findings

    @staticmethod
    def parse_nwchem_output(path: str) -> List[Dict[str, Any]]:
        """Parse an NWChem output file from a filesystem path.

        Args:
            path: Filesystem path to the NWChem output file.

        Returns:
            List of finding dicts (same as :meth:`parse_log`).

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"NWChem output file not found: {path}")
        text = p.read_text(errors="replace")
        return AgentAPIProvider.parse_log(text)

    # ------------------------------------------------------------------
    # Capability #84: Rule manifest and OpenQC smoke test
    # ------------------------------------------------------------------

    @staticmethod
    def get_rule_manifest() -> Dict[str, Any]:
        """Return the full rule code catalog with descriptions.

        Returns:
            Dictionary mapping rule codes to their descriptions,
            plus metadata about the NWChem LSP implementation.
        """
        return {
            "provider": "nwchem-lsp",
            "language": "nwchem",
            "version": "1.0.0",
            "rules": {
                code: desc for code, desc in RULE_DESCRIPTIONS.items()
            },
            "rule_count": len(RULE_DESCRIPTIONS),
            "categories": {
                "syntax": [
                    c for c in RULE_DESCRIPTIONS if c.startswith("NW1")
                ],
                "schema": [
                    c for c in RULE_DESCRIPTIONS if c.startswith("NW2")
                ],
                "best_practice": [
                    c for c in RULE_DESCRIPTIONS if c.startswith("NW3")
                ],
                "issue_mapped": [
                    c for c in RULE_DESCRIPTIONS if c.startswith("NWCHEM-")
                ],
            },
        }

    @staticmethod
    def openqc_smoke() -> Dict[str, Any]:
        """Run a lightweight smoke test for OpenQC integration.

        Validates that the NWChem LSP provider can be instantiated and
        that core APIs return expected shapes.

        Returns:
            Dictionary with ``status`` (``"pass"`` or ``"fail"``),
            ``checks``, and ``error`` (if any).
        """
        checks: List[Dict[str, Any]] = []

        # Check 1: Lint provider instantiation
        try:
            lint = NwchemLintProvider()
            diags = lint.lint("geometry\n  H 0 0 0\nend\nbasis\n  * library 6-31g\nend\ntask scf energy\n")
            checks.append(
                {
                    "name": "lint_provider",
                    "status": "pass",
                    "diagnostic_count": len(diags),
                }
            )
        except Exception as exc:
            checks.append(
                {"name": "lint_provider", "status": "fail", "error": str(exc)}
            )

        # Check 2: Domain language description
        try:
            desc = AgentAPIProvider.describe_domain_language()
            has_sections = "sections" in desc and len(desc["sections"]) > 0
            checks.append(
                {
                    "name": "describe_domain_language",
                    "status": "pass" if has_sections else "fail",
                    "section_count": len(desc.get("sections", [])),
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "name": "describe_domain_language",
                    "status": "fail",
                    "error": str(exc),
                }
            )

        # Check 3: Schema lookup
        try:
            geo = AgentAPIProvider.lookup_section("geometry")
            ok = geo is not None and geo.get("required") is True
            checks.append(
                {
                    "name": "lookup_section",
                    "status": "pass" if ok else "fail",
                }
            )
        except Exception as exc:
            checks.append(
                {"name": "lookup_section", "status": "fail", "error": str(exc)}
            )

        # Check 4: Keyword lookup
        try:
            xc = AgentAPIProvider.lookup_keyword("dft", "xc")
            ok = xc is not None and "description" in xc
            checks.append(
                {
                    "name": "lookup_keyword",
                    "status": "pass" if ok else "fail",
                }
            )
        except Exception as exc:
            checks.append(
                {"name": "lookup_keyword", "status": "fail", "error": str(exc)}
            )

        # Check 5: Examples
        try:
            examples = AgentAPIProvider.get_examples()
            ok = len(examples) > 0 and all("source" in e for e in examples)
            checks.append(
                {
                    "name": "get_examples",
                    "status": "pass" if ok else "fail",
                    "example_count": len(examples),
                }
            )
        except Exception as exc:
            checks.append(
                {"name": "get_examples", "status": "fail", "error": str(exc)}
            )

        # Check 6: Token suggestions
        try:
            suggestions = AgentAPIProvider.next_token_suggestions("task_theory")
            ok = len(suggestions) > 0
            checks.append(
                {
                    "name": "next_token_suggestions",
                    "status": "pass" if ok else "fail",
                    "suggestion_count": len(suggestions),
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "name": "next_token_suggestions",
                    "status": "fail",
                    "error": str(exc),
                }
            )

        # Check 7: Log parser
        try:
            findings = AgentAPIProvider.parse_log(
                "SCF failed to converge after 100 iterations\n"
                "Total SCF energy = -76.0234\n"
            )
            ok = len(findings) >= 2
            checks.append(
                {
                    "name": "parse_log",
                    "status": "pass" if ok else "fail",
                    "finding_count": len(findings),
                }
            )
        except Exception as exc:
            checks.append(
                {"name": "parse_log", "status": "fail", "error": str(exc)}
            )

        # Check 8: Rule manifest
        try:
            manifest = AgentAPIProvider.get_rule_manifest()
            ok = "rules" in manifest and len(manifest["rules"]) > 0
            checks.append(
                {
                    "name": "get_rule_manifest",
                    "status": "pass" if ok else "fail",
                    "rule_count": len(manifest.get("rules", {})),
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "name": "get_rule_manifest",
                    "status": "fail",
                    "error": str(exc),
                }
            )

        all_passed = all(c["status"] == "pass" for c in checks)
        return {
            "status": "pass" if all_passed else "fail",
            "checks": checks,
            "check_count": len(checks),
            "passed": sum(1 for c in checks if c["status"] == "pass"),
            "failed": sum(1 for c in checks if c["status"] == "fail"),
        }

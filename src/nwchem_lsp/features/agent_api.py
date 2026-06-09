"""Machine-readable code-intelligence API for AI coding agents.

Provides structured JSON endpoints for Claude Code, OpenCode, Codex,
and other agent workflows. Endpoints expose diagnostics, symbols,
hover information, and document structure without requiring LSP protocol.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .diagnostic import DiagnosticProvider
from .lint import NwchemLintProvider


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
    """Provides machine-readable code intelligence for AI agents."""

    def __init__(
        self,
        diagnostic_provider: Optional[DiagnosticProvider] = None,
        lint_provider: Optional[NwchemLintProvider] = None,
        
    ) -> None:
        self._diagnostic = diagnostic_provider
        self._lint = lint_provider
        

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
                outline.append({"type": "module_start", "line": i, "name": stripped.split()[1] if len(stripped.split()) > 1 else ""})
            elif stripped.startswith("task "):
                outline.append({"type": "task", "line": i, "text": stripped})
            elif not stripped.startswith("end") and (
                stripped in ("geometry", "basis", "scf", "dft", "mp2", "ccsd", "tce")
                or stripped.startswith("geometry ")
                or stripped.startswith("basis ")
            ):
                outline.append({"type": "section", "line": i, "name": stripped.split()[0]})

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

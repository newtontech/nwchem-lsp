"""LSP workspace symbols provider for NWChem.

This module provides workspace-wide symbols for NWChem input files,
enabling global symbol search across all open documents.
"""

import re
from typing import List, Optional

from lsprotocol.types import (
    Location,
    Position,
    Range,
    SymbolKind,
    WorkspaceSymbol,
)
from pygls.server import LanguageServer

from ..parser.nwchem_parser import NwchemParser, NWchemSection


class WorkspaceSymbolProvider:
    """Provides workspace symbols for NWChem input files."""

    # Map section names to symbol kinds
    SYMBOL_KINDS = {
        "geometry": SymbolKind.Class,
        "basis": SymbolKind.Class,
        "scf": SymbolKind.Method,
        "dft": SymbolKind.Method,
        "mp2": SymbolKind.Method,
        "ccsd": SymbolKind.Method,
        "ccsd(t)": SymbolKind.Method,
        "task": SymbolKind.Function,
        "property": SymbolKind.Property,
        "vib": SymbolKind.Method,
        "hessian": SymbolKind.Method,
        "tce": SymbolKind.Method,
        "mcscf": SymbolKind.Method,
        "ecp": SymbolKind.Class,
        "charge": SymbolKind.Property,
    }

    def __init__(self, server: LanguageServer):
        """Initialize the workspace symbol provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_workspace_symbols(self, query: str, documents: dict[str, str]) -> List[WorkspaceSymbol]:
        """Get workspace symbols matching the query.

        Args:
            query: Search query string
            documents: Dictionary mapping URIs to document text

        Returns:
            List of workspace symbols
        """
        symbols: List[WorkspaceSymbol] = []
        query_lower = query.lower()

        for uri, text in documents.items():
            parser = NwchemParser(text)

            for section_name, sections in parser.sections.items():
                # Filter by query
                if query and not (
                    query_lower in section_name.lower()
                    or any(query_lower in kw.lower() for kw in sections[0].keywords)
                ):
                    continue

                for section in sections:
                    symbol = self._create_workspace_symbol(section, uri)
                    if symbol:
                        symbols.append(symbol)

            # Add title/start as symbol if query matches
            title = self._get_title(text)
            if title and (not query or query_lower in title.lower()):
                symbols.append(
                    WorkspaceSymbol(
                        name=f"📄 {title}",
                        kind=SymbolKind.File,
                        location=Location(
                            uri=uri,
                            range=Range(
                                start=Position(line=0, character=0),
                                end=Position(line=0, character=len(title)),
                            ),
                        ),
                    )
                )

        return symbols

    def _get_title(self, text: str) -> Optional[str]:
        """Extract title from NWChem input.

        Args:
            text: Document text

        Returns:
            Title string or None
        """
        lines = text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            # Match title "..." or title ...
            match = re.match(r'^title\s+["\']?(.+?)["\']?$', line_stripped, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            # Match start ...
            match = re.match(r"^start\s+(\S+)$", line_stripped, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _create_workspace_symbol(
        self, section: NWchemSection, uri: str
    ) -> Optional[WorkspaceSymbol]:
        """Create a WorkspaceSymbol from a section.

        Args:
            section: Parsed NWChem section
            uri: Document URI

        Returns:
            WorkspaceSymbol object or None
        """
        end_line = section.end_line if section.end_line is not None else section.start_line

        detail = f"Section with {len(section.keywords)} keywords"
        if section.keywords:
            detail += f": {', '.join(section.keywords[:3])}"
            if len(section.keywords) > 3:
                detail += "..."

        return WorkspaceSymbol(
            name=section.name.upper(),
            kind=self.SYMBOL_KINDS.get(section.name, SymbolKind.Module),
            location=Location(
                uri=uri,
                range=Range(
                    start=Position(line=section.start_line, character=0),
                    end=Position(line=end_line, character=0),
                ),
            ),
            container_name="NWChem Input",
        )

    def resolve_workspace_symbol(self, symbol: WorkspaceSymbol) -> Optional[WorkspaceSymbol]:
        """Resolve a workspace symbol (for lazy resolution).

        Args:
            symbol: Partial symbol to resolve

        Returns:
            Fully resolved symbol or None
        """
        return symbol


def get_workspace_symbol_provider(server: LanguageServer) -> WorkspaceSymbolProvider:
    """Create a workspace symbol provider instance.

    Args:
        server: The language server instance

    Returns:
        Workspace symbol provider instance
    """
    return WorkspaceSymbolProvider(server)

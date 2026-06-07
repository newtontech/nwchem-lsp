"""LSP document symbols provider for NWChem.

This module provides document symbols for NWChem input files,
enabling outline view and navigation.
"""

from typing import List

from lsprotocol.types import (
    DocumentSymbol,
    Position,
    Range,
    SymbolKind,
)
from pygls.server import LanguageServer

from ..parser.nwchem_parser import NwchemParser, NWchemSection


class NwchemSymbolProvider:
    """Provides document symbols for NWChem input files."""

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
    }

    def __init__(self, server: LanguageServer):
        """Initialize the symbol provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_document_symbols(self, text: str) -> List[DocumentSymbol]:
        """Get document symbols for the given text.

        Args:
            text: Document text

        Returns:
            List of document symbols
        """
        parser = NwchemParser(text)
        symbols: List[DocumentSymbol] = []

        for section_name, sections in parser.sections.items():
            for section in sections:
                symbol = self._create_symbol(section)
                if symbol:
                    symbols.append(symbol)

        return symbols

    def _create_symbol(self, section: NWchemSection) -> DocumentSymbol:
        """Create a DocumentSymbol from a section.

        Args:
            section: Parsed NWChem section

        Returns:
            DocumentSymbol object
        """
        end_line = section.end_line if section.end_line is not None else section.start_line

        return DocumentSymbol(
            name=section.name.upper(),
            kind=self.SYMBOL_KINDS.get(section.name, SymbolKind.Module),
            range=Range(
                start=Position(line=section.start_line, character=0),
                end=Position(line=end_line, character=0),
            ),
            selection_range=Range(
                start=Position(line=section.start_line, character=0),
                end=Position(line=section.start_line, character=len(section.name)),
            ),
            children=[],
            detail=f"Section with {len(section.keywords)} keywords",
        )


# Alias for backwards compatibility
SymbolProvider = NwchemSymbolProvider


def get_symbol_provider(server: LanguageServer) -> NwchemSymbolProvider:
    """Create a symbol provider instance.

    Args:
        server: The language server instance

    Returns:
        Symbol provider instance
    """
    return NwchemSymbolProvider(server)

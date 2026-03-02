"""Parser package for nwchem-lsp."""

from .nwchem_parser import NwchemParser, NWchemSection, ParseContext

# Alias for backwards compatibility
NWChemParser = NwchemParser

__all__ = ["NwchemParser", "NWChemParser", "ParseContext", "NWchemSection"]

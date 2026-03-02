"""Parser package for nwchem-lsp."""

from .nwchem_parser import NwchemParser, ParseContext, NWchemSection

# Alias for backwards compatibility
NWChemParser = NwchemParser

__all__ = ["NwchemParser", "NWChemParser", "ParseContext", "NWchemSection"]

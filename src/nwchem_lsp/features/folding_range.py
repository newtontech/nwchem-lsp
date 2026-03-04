"""LSP folding range provider for NWChem.

This module provides folding range support for NWChem input files,
enabling code folding for sections and blocks.
"""

from typing import List, Optional

from lsprotocol.types import (
    FoldingRange,
    FoldingRangeKind,
)
from pygls.server import LanguageServer

from ..parser.nwchem_parser import NwchemParser


class FoldingRangeProvider:
    """Provides folding ranges for NWChem input files."""

    def __init__(self, server: Optional[LanguageServer] = None):
        """Initialize the folding range provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_folding_ranges(self, text: str) -> List[FoldingRange]:
        """Get folding ranges for the given text.

        Args:
            text: Document text

        Returns:
            List of folding ranges
        """
        parser = NwchemParser(text)
        ranges: List[FoldingRange] = []

        # Add folding ranges for sections
        for section_name, sections in parser.sections.items():
            for section in sections:
                if section.end_line is not None and section.end_line > section.start_line:
                    ranges.append(
                        FoldingRange(
                            start_line=section.start_line,
                            end_line=section.end_line,
                            kind=FoldingRangeKind.Region,
                            collapsed_text=f"{section.name} ... end",
                        )
                    )

        return ranges

    def get_folding_ranges_for_lines(
        self, text: str, start_line: int, end_line: int
    ) -> List[FoldingRange]:
        """Get folding ranges for a specific line range.

        Args:
            text: Document text
            start_line: Start line number
            end_line: End line number

        Returns:
            List of folding ranges within the specified range
        """
        all_ranges = self.get_folding_ranges(text)
        return [
            r for r in all_ranges
            if r.start_line >= start_line and r.end_line <= end_line
        ]


def get_folding_range_provider(server: Optional[LanguageServer] = None) -> FoldingRangeProvider:
    """Create a folding range provider instance.

    Args:
        server: The language server instance

    Returns:
        Folding range provider instance
    """
    return FoldingRangeProvider(server)

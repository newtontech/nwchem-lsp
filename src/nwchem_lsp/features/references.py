"""LSP references provider for NWChem.

This module provides find-references support for NWChem input files,
enabling users to find all references to a symbol.
"""

from typing import List, Optional

from lsprotocol.types import (
    Location,
    Position,
    Range,
    TextDocumentIdentifier,
)
from pygls.server import LanguageServer

from ..parser.nwchem_parser import NwchemParser


class ReferencesProvider:
    """Provides references support for NWChem input files."""

    def __init__(self, server: Optional[LanguageServer] = None):
        """Initialize the references provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_references(
        self,
        text: str,
        uri: str,
        position: Position,
        include_declaration: bool = True,
    ) -> List[Location]:
        """Get references to the symbol at the given position.

        Args:
            text: Document text
            uri: Document URI
            position: Cursor position
            include_declaration: Whether to include declaration in results

        Returns:
            List of locations referencing the symbol
        """
        parser = NwchemParser(text)
        line_num = position.line
        col = position.character

        # Get the word at cursor
        lines = text.splitlines()
        if line_num >= len(lines):
            return []

        line = lines[line_num]
        word = self._get_word_at_position(line, col)

        if not word:
            return []

        word_lower = word.lower()
        locations: List[Location] = []

        # Check if word is a section name
        if word_lower in parser.SECTION_KEYWORDS:
            # Find all occurrences of this section
            for section_name, sections in parser.sections.items():
                if section_name == word_lower:
                    for section in sections:
                        # Add the section start
                        if include_declaration:
                            locations.append(
                                Location(
                                    uri=uri,
                                    range=Range(
                                        start=Position(line=section.start_line, character=0),
                                        end=Position(
                                            line=section.start_line,
                                            character=len(section_name),
                                        ),
                                    ),
                                )
                            )
                        # Add the end keyword if present
                        if section.end_line is not None:
                            end_line_text = lines[section.end_line].strip().lower()
                            if end_line_text == "end":
                                locations.append(
                                    Location(
                                        uri=uri,
                                        range=Range(
                                            start=Position(line=section.end_line, character=0),
                                            end=Position(line=section.end_line, character=3),
                                        ),
                                    )
                                )

        return locations

    def _get_word_at_position(self, line: str, column: int) -> str:
        """Extract the word at a specific column position.

        Args:
            line: The line text
            column: The column position

        Returns:
            The word at the position
        """
        if not line or column < 0 or column > len(line):
            return ""

        start = column
        end = column

        while start > 0 and (line[start - 1].isalnum() or line[start - 1] in "_()"):
            start -= 1

        while end < len(line) and (line[end].isalnum() or line[end] in "_()"):
            end += 1

        return line[start:end]


def get_references_provider(server: Optional[LanguageServer] = None) -> ReferencesProvider:
    """Create a references provider instance.

    Args:
        server: The language server instance

    Returns:
        References provider instance
    """
    return ReferencesProvider(server)

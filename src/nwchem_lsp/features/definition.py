"""Definition provider for NWChem LSP.

Provides go-to-definition functionality for NWChem input files.
"""

from typing import Optional

from lsprotocol.types import Location, Position, Range, TextDocumentIdentifier

from ..parser.nwchem_parser import NwchemParser


class DefinitionProvider:
    """Provides go-to-definition functionality for NWChem input files."""

    def __init__(self) -> None:
        """Initialize definition provider."""
        pass

    def get_definition(
        self, source: str, position: Position
    ) -> Optional[Location]:
        """Get definition location for the symbol at the given position.

        Args:
            source: The document source text
            position: The cursor position

        Returns:
            Location of the definition, or None if not found
        """
        lines = source.split("\n")
        if position.line >= len(lines):
            return None

        line = lines[position.line]
        word = self._get_word_at_position(line, position.character)

        if not word:
            return None

        word_lower = word.lower()

        # Handle 'end' keyword - jump to corresponding section start
        if word_lower == "end":
            return self._find_section_start(source, position.line)

        # Handle section keywords - jump to section start if we're on an 'end'
        if word_lower in NwchemParser.SECTION_KEYWORDS:
            # Check if we're on an 'end' line that closes this section type
            stripped = line.strip().lower()
            if stripped == "end":
                return self._find_section_start_by_type(source, word_lower, position.line)

        return None

    def _get_word_at_position(self, line: str, column: int) -> str:
        """Extract the word at a specific column position."""
        if not line or column < 0 or column > len(line):
            return ""

        # Find word boundaries
        start = column
        end = column

        # Move start to beginning of word
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        # Move end to end of word
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        return line[start:end]

    def _find_section_start(self, source: str, end_line_num: int) -> Optional[Location]:
        """Find the section start corresponding to an 'end' keyword.

        Args:
            source: The document source text
            end_line_num: The line number containing 'end'

        Returns:
            Location of the section start, or None if not found
        """
        lines = source.split("\n")

        # Track open sections from the beginning up to end_line
        section_stack: list[tuple[str, int]] = []

        for i in range(end_line_num):
            line = lines[i]
            stripped = line.strip().lower()

            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if not parts:
                continue

            keyword = parts[0]

            if keyword in NwchemParser.SECTION_KEYWORDS:
                section_stack.append((keyword, i))
            elif keyword == "end" and section_stack:
                section_stack.pop()

        # The last item on the stack is the section this 'end' closes
        if section_stack:
            section_name, start_line = section_stack[-1]
            return Location(
                uri="",
                range=Range(
                    start=Position(line=start_line, character=0),
                    end=Position(line=start_line, character=len(lines[start_line])),
                ),
            )

        return None

    def _find_section_start_by_type(
        self, source: str, section_type: str, before_line: int
    ) -> Optional[Location]:
        """Find the start of a specific section type before the given line.

        Args:
            source: The document source text
            section_type: The type of section to find
            before_line: Only look at lines before this

        Returns:
            Location of the section start, or None if not found
        """
        lines = source.split("\n")
        section_type_lower = section_type.lower()

        # Track open sections
        section_stack: list[tuple[str, int]] = []

        for i in range(before_line):
            line = lines[i]
            stripped = line.strip().lower()

            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if not parts:
                continue

            keyword = parts[0]

            if keyword in NwchemParser.SECTION_KEYWORDS:
                section_stack.append((keyword, i))
            elif keyword == "end" and section_stack:
                section_stack.pop()

        # Find the last occurrence of the requested section type
        for section_name, line_num in reversed(section_stack):
            if section_name == section_type_lower:
                return Location(
                    uri="",
                    range=Range(
                        start=Position(line=line_num, character=0),
                        end=Position(line=line_num, character=len(lines[line_num])),
                    ),
                )

        return None


def get_definition_provider() -> DefinitionProvider:
    """Factory function to create a definition provider.

    Returns:
        A new DefinitionProvider instance.
    """
    return DefinitionProvider()

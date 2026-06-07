"""LSP rename provider for NWChem.

This module provides rename refactoring support for NWChem input files.
"""

from typing import Dict, List, Optional

from lsprotocol.types import (
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)
from pygls.server import LanguageServer

from ..parser.nwchem_parser import NwchemParser


class RenameProvider:
    """Provides rename support for NWChem input files."""

    def __init__(self, server: Optional[LanguageServer] = None):
        """Initialize the rename provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_rename_edits(
        self,
        text: str,
        uri: str,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        """Get workspace edits for renaming a symbol.

        Args:
            text: Document text
            uri: Document URI
            position: Cursor position
            new_name: The new name for the symbol

        Returns:
            WorkspaceEdit with changes, or None if rename is not valid
        """
        parser = NwchemParser(text)
        line_num = position.line
        col = position.character

        # Get the word at cursor
        lines = text.splitlines()
        if line_num >= len(lines):
            return None

        line = lines[line_num]
        word = self._get_word_at_position(line, col)

        if not word:
            return None

        word_lower = word.lower()

        # Only allow renaming sections
        if word_lower not in parser.SECTION_KEYWORDS:
            return None

        # Check if new name is a valid section keyword
        if new_name.lower() not in parser.SECTION_KEYWORDS:
            return None

        changes: Dict[str, List[TextEdit]] = {uri: []}

        # Find all occurrences of this section
        for section_name, sections in parser.sections.items():
            if section_name == word_lower:
                for section in sections:
                    # Rename the section start
                    changes[uri].append(
                        TextEdit(
                            range=Range(
                                start=Position(line=section.start_line, character=0),
                                end=Position(
                                    line=section.start_line,
                                    character=len(section_name),
                                ),
                            ),
                            new_text=new_name.lower(),
                        )
                    )

        if not changes[uri]:
            return None

        return WorkspaceEdit(changes=changes)

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

    def is_valid_rename(
        self,
        text: str,
        position: Position,
        new_name: str,
    ) -> bool:
        """Check if a rename operation is valid.

        Args:
            text: Document text
            position: Cursor position
            new_name: The new name for the symbol

        Returns:
            True if rename is valid
        """
        parser = NwchemParser(text)
        line_num = position.line
        col = position.character

        lines = text.splitlines()
        if line_num >= len(lines):
            return False

        line = lines[line_num]
        word = self._get_word_at_position(line, col)

        if not word:
            return False

        # Can only rename section keywords
        if word.lower() not in parser.SECTION_KEYWORDS:
            return False

        # New name must also be a valid section keyword
        if new_name.lower() not in parser.SECTION_KEYWORDS:
            return False

        return True


def get_rename_provider(server: Optional[LanguageServer] = None) -> RenameProvider:
    """Create a rename provider instance.

    Args:
        server: The language server instance

    Returns:
        Rename provider instance
    """
    return RenameProvider(server)

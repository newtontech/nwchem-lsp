"""LSP hover provider for NWChem.

This module provides hover documentation for NWChem keywords.
"""

from typing import Any, Optional

from lsprotocol.types import Hover, HoverParams, MarkupContent, MarkupKind, Position
from pygls.server import LanguageServer
from pygls.workspace import TextDocument

from ..data.keywords import (
    BASIS_KEYWORDS,
    DFT_KEYWORDS,
    GEOMETRY_KEYWORDS,
    KeywordInfo,
    SCF_KEYWORDS,
    TOP_LEVEL_KEYWORDS,
    get_keyword_info,
    get_section_keywords,
    is_valid_keyword,
)
from ..parser.nwchem_parser import NwchemParser


class NwchemHoverProvider:
    """Provides hover information for NWChem input files."""

    def __init__(self, server: LanguageServer):
        """Initialize the hover provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_hover(self, text: str, position: Position) -> Optional[Hover]:
        """Get hover information for the given position.

        Args:
            text: Document text
            position: Position in the document

        Returns:
            Hover object or None
        """
        source = text
        line_number = position.line
        column = position.character

        # Parse to get context
        parser = NwchemParser(source)
        context = parser.get_context(line_number, column)

        word = context.word_at_cursor
        if not word:
            return None

        word_lower = word.lower()

        # Determine section context
        section = context.current_section or "top"

        # Try to get keyword info from specific section first
        info = get_keyword_info(word_lower, section)

        # Fall back to top-level if not found
        if info is None:
            info = get_keyword_info(word_lower, "top")

        if info:
            return self._create_hover(info)

        return None

    def _create_hover(self, info: KeywordInfo) -> Hover:
        """Create a Hover object from keyword info.

        Args:
            info: KeywordInfo object

        Returns:
            Hover object
        """
        content_lines = [
            f"**{info.name}**",
            "",
            info.description,
        ]

        if info.arguments:
            content_lines.extend(
                [
                    "",
                    "**Arguments:**",
                    ", ".join(f"`{arg}`" for arg in info.arguments[:10]),
                ]
            )
            if len(info.arguments) > 10:
                content_lines[-1] += f" (and {len(info.arguments) - 10} more...)"

        if info.example:
            content_lines.extend(
                [
                    "",
                    "**Example:**",
                    "```",
                    info.example,
                    "```",
                ]
            )

        if info.required:
            content_lines.extend(["", "*Required*"])

        content = "\n".join(content_lines)

        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=content,
            )
        )

    def get_word_at_position(self, document: TextDocument, position: Position) -> str:
        """Get the word at the given position.

        Args:
            document: The text document
            position: The position

        Returns:
            The word at the position
        """
        if position.line >= len(document.lines):
            return ""
        line = document.lines[position.line]
        if not line:
            return ""

        # Find word boundaries
        start = position.character
        end = position.character

        while start > 0 and line[start - 1].isalnum():
            start -= 1

        while end < len(line) and line[end].isalnum():
            end += 1

        return line[start:end]


# Alias for backwards compatibility
HoverProvider = NwchemHoverProvider


def get_hover_provider(server: LanguageServer) -> NwchemHoverProvider:
    """Create a hover provider instance.

    Args:
        server: The language server instance

    Returns:
        Hover provider instance
    """
    return NwchemHoverProvider(server)

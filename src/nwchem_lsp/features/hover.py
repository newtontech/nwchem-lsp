"""LSP hover provider for NWChem.

This module provides hover documentation for NWChem keywords.
"""

from typing import Optional

from lsprotocol.types import Hover, HoverParams, MarkupContent, MarkupKind, Position
from pygls.server import LanguageServer

from ..data.keywords import (
    TOP_LEVEL_KEYWORDS,
    DFT_KEYWORDS,
    SCF_KEYWORDS,
    GEOMETRY_KEYWORDS,
    BASIS_KEYWORDS,
    get_keyword_info,
    is_valid_keyword,
    get_section_keywords,
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

    def get_hover(self, params: HoverParams) -> Optional[Hover]:
        """Get hover information for the given position.
        
        Args:
            params: Hover parameters from LSP client
            
        Returns:
            Hover object or None
        """
        document = self.server.workspace.get_text_document(params.text_document.uri)
        source = document.source
        line_number = params.position.line
        column = params.position.character

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

    def _create_hover(self, info) -> Hover:
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
            content_lines.extend([
                "",
                "**Arguments:**",
                ", ".join(f"`{arg}`" for arg in info.arguments[:10]),
            ])
            if len(info.arguments) > 10:
                content_lines[-1] += f" (and {len(info.arguments) - 10} more...)"

        if info.example:
            content_lines.extend([
                "",
                "**Example:**",
                "```",
                info.example,
                "```",
            ])

        if info.required:
            content_lines.extend(["", "*Required*"])

        content = "\n".join(content_lines)

        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=content,
            )
        )

    def get_word_at_position(
        self, document, position: Position
    ) -> str:
        """Get the word at the given position.
        
        Args:
            document: The text document
            position: The position
            
        Returns:
            The word at the position
        """
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


def get_hover_provider(server: LanguageServer) -> NwchemHoverProvider:
    """Create a hover provider instance.
    
    Args:
        server: The language server instance
        
    Returns:
        Hover provider instance
    """
    return NwchemHoverProvider(server)

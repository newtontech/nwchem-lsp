"""LSP formatting provider for NWChem.

This module provides code formatting for NWChem input files.
"""

from typing import List, Optional

from lsprotocol.types import (
    DocumentFormattingParams,
    Position,
    Range,
    TextEdit,
)
from pygls.server import LanguageServer


class NwchemFormattingProvider:
    """Provides formatting for NWChem input files."""

    def __init__(self, server: LanguageServer):
        """Initialize the formatting provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def format_document(
        self, text: str, params: DocumentFormattingParams
    ) -> List[TextEdit]:
        """Format the entire document.

        Args:
            text: Document text
            params: Formatting parameters

        Returns:
            List of text edits to apply
        """
        lines = text.splitlines()
        formatted_lines = []
        edits: List[TextEdit] = []

        indent_size = params.options.tab_size if params.options else 2
        indent_str = " " * indent_size if not (params.options and params.options.insert_spaces) else "\t"
        
        current_indent = 0
        in_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped:
                formatted_lines.append("")
                continue
            
            if stripped.startswith("#"):
                formatted_lines.append(stripped)
                continue
            
            # Check for section end
            if stripped.lower() == "end":
                current_indent = max(0, current_indent - 1)
                in_section = False
                formatted_lines.append(indent_str * current_indent + stripped)
                continue
            
            # Check for section start
            parts = stripped.split()
            if parts and parts[0].lower() in self._get_section_keywords():
                formatted_lines.append(stripped)
                current_indent += 1
                in_section = True
                continue
            
            # Regular line - apply current indentation
            if in_section:
                formatted_lines.append(indent_str * current_indent + stripped)
            else:
                formatted_lines.append(stripped)

        # Create a single edit replacing the entire document
        formatted_text = "\n".join(formatted_lines)
        if text.endswith("\n"):
            formatted_text += "\n"

        if formatted_text != text:
            edits.append(
                TextEdit(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=len(lines), character=0),
                    ),
                    new_text=formatted_text,
                )
            )

        return edits

    def _get_section_keywords(self) -> set:
        """Get set of section keywords.

        Returns:
            Set of section keyword names
        """
        return {
            "geometry",
            "basis",
            "scf",
            "dft",
            "mp2",
            "ccsd",
            "ccsd(t)",
            "ecp",
            "so",
            "tce",
            "mcscf",
            "selci",
            "hessian",
            "vib",
            "property",
            "rt_tddft",
            "pspw",
            "band",
            "paw",
            "ofpw",
            "bq",
            "charge",
            "cons",
        }


# Alias for backwards compatibility
FormattingProvider = NwchemFormattingProvider


def get_formatting_provider(server: LanguageServer) -> NwchemFormattingProvider:
    """Create a formatting provider instance.

    Args:
        server: The language server instance

    Returns:
        Formatting provider instance
    """
    return NwchemFormattingProvider(server)

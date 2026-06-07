"""LSP completion provider for NWChem.

This module provides keyword completions based on the current context
in an NWChem input file.
"""

import logging
from typing import Any, List, Optional

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    Position,
)
from pygls.server import LanguageServer

from ..data.keywords import (
    BASIS_KEYWORDS,
    BASIS_SETS,
    DFT_FUNCTIONALS,
    DFT_KEYWORDS,
    GEOMETRY_KEYWORDS,
    SCF_KEYWORDS,
    TASK_OPERATIONS,
    TOP_LEVEL_KEYWORDS,
    get_keyword_info,
    get_keywords_by_section,
)
from ..parser.nwchem_parser import NwchemParser

logger = logging.getLogger(__name__)


def _matches_prefix(item: str, prefix: str) -> bool:
    """Check whether *item* starts with *prefix* (case-insensitive).

    Returns ``True`` when *prefix* is empty so that callers can use
    ``if not _matches_prefix(...): continue`` without an extra guard.
    """
    if not prefix:
        return True
    return item.lower().startswith(prefix.lower())


def _make_completion_item(
    label: str,
    kind: CompletionItemKind,
    detail: str = "",
    documentation: str = "",
) -> CompletionItem:
    """Factory helper to reduce repeated CompletionItem construction."""
    return CompletionItem(
        label=label,
        kind=kind,
        detail=detail or None,
        documentation=documentation or None,
    )


class NwchemCompletionProvider:
    """Provides completion items for NWChem input files."""

    def __init__(self, server: LanguageServer):
        """Initialize the completion provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_completions(self, text: str, position: Position) -> List[CompletionItem]:
        """Get completion items for the given position.

        Args:
            text: Document text
            position: Position in the document

        Returns:
            List of completion items
        """
        source = text
        line_number = position.line
        column = position.character

        # Parse the source to get context
        try:
            parser = NwchemParser(source)
            context = parser.get_completion_context(line_number, column)
        except Exception:
            logger.exception("Error parsing source for completions")
            return []

        completion_type = context.get("type", "top_level")
        current_word = context.get("word", "")

        # Return completions based on context
        if completion_type == "dft_functional":
            return self._get_dft_functional_completions(current_word)
        elif completion_type == "basis_set":
            return self._get_basis_set_completions(current_word)
        elif completion_type == "task_operation":
            return self._get_task_operation_completions(current_word)
        elif completion_type == "dft":
            return self._get_section_completions("dft", current_word)
        elif completion_type == "scf":
            return self._get_section_completions("scf", current_word)
        elif completion_type == "geometry":
            return self._get_section_completions("geometry", current_word)
        elif completion_type == "basis":
            return self._get_section_completions("basis", current_word)
        else:
            return self._get_top_level_completions(current_word)

    def _get_top_level_completions(self, prefix: str = "") -> List[CompletionItem]:
        """Get top-level keyword completions.

        Args:
            prefix: Current word prefix to filter by

        Returns:
            List of completion items
        """
        items: List[CompletionItem] = []

        for name, info in TOP_LEVEL_KEYWORDS.items():
            if not _matches_prefix(name, prefix):
                continue

            items.append(
                _make_completion_item(
                    label=name,
                    kind=CompletionItemKind.Keyword,
                    detail=info.description,
                    documentation=info.example or "",
                )
            )

        return items

    def _get_section_completions(self, section: str, prefix: str = "") -> List[CompletionItem]:
        """Get completions for a specific section.

        Args:
            section: Section name (e.g., 'dft', 'scf')
            prefix: Current word prefix

        Returns:
            List of completion items
        """
        items: List[CompletionItem] = []
        keywords = get_keywords_by_section(section)

        for kw in keywords:
            name = kw.name
            if not _matches_prefix(name, prefix):
                continue

            info = get_keyword_info(name, section)
            items.append(
                _make_completion_item(
                    label=name,
                    kind=CompletionItemKind.Property,
                    detail=info.description if info else "",
                    documentation=info.example or "" if info else "",
                )
            )

        return items

    def _get_dft_functional_completions(self, prefix: str = "") -> List[CompletionItem]:
        """Get DFT functional completions.

        Args:
            prefix: Current word prefix

        Returns:
            List of completion items
        """
        items: List[CompletionItem] = []

        for functional in DFT_FUNCTIONALS:
            if not _matches_prefix(functional, prefix):
                continue

            items.append(
                _make_completion_item(
                    label=functional,
                    kind=CompletionItemKind.Value,
                    detail=f"DFT Functional: {functional}",
                )
            )

        return items

    def _get_basis_set_completions(self, prefix: str = "") -> List[CompletionItem]:
        """Get basis set completions.

        Args:
            prefix: Current word prefix

        Returns:
            List of completion items
        """
        items: List[CompletionItem] = []

        for basis in BASIS_SETS:
            if not _matches_prefix(basis, prefix):
                continue

            items.append(
                _make_completion_item(
                    label=basis,
                    kind=CompletionItemKind.Value,
                    detail=f"Basis Set: {basis}",
                )
            )

        return items

    def _get_task_operation_completions(self, prefix: str = "") -> List[CompletionItem]:
        """Get task operation completions.

        Args:
            prefix: Current word prefix

        Returns:
            List of completion items
        """
        items: List[CompletionItem] = []

        for operation in TASK_OPERATIONS:
            if not _matches_prefix(operation, prefix):
                continue

            items.append(
                _make_completion_item(
                    label=operation,
                    kind=CompletionItemKind.EnumMember,
                    detail=f"Task: {operation}",
                )
            )

        return items

    def _get_element_completions(self, prefix: str = "") -> List[CompletionItem]:
        """Get chemical element completions.

        Args:
            prefix: Current word prefix

        Returns:
            List of completion items
        """
        items: List[CompletionItem] = []

        for element in ELEMENTS:
            if not _matches_prefix(element, prefix):
                continue

            items.append(
                _make_completion_item(
                    label=element,
                    kind=CompletionItemKind.Constant,
                    detail=f"Element: {element}",
                )
            )

        return items

# Alias for backwards compatibility
CompletionProvider = NwchemCompletionProvider


def get_completion_provider(server: LanguageServer) -> NwchemCompletionProvider:
    """Create a completion provider instance.

    Args:
        server: The language server instance

    Returns:
        Completion provider instance
    """
    return NwchemCompletionProvider(server)

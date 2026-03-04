"""LSP semantic tokens provider for NWChem.

This module provides semantic highlighting for NWChem input files,
enabling color-coded syntax based on token types.
"""

from typing import List, Optional

from lsprotocol.types import (
    Position,
    Range,
    SemanticTokens,
    SemanticTokensLegend,
    SemanticTokensParams,
    SemanticTokenModifiers,
    SemanticTokenTypes,
)
from pygls.server import LanguageServer

from ..data.keywords import (
    BASIS_SETS,
    DFT_FUNCTIONALS,
    ELEMENTS,
    TASK_OPERATIONS,
)
from ..parser.nwchem_parser import NwchemParser


class SemanticTokensProvider:
    """Provides semantic tokens for NWChem input files."""

    # Token types in order of legend
    TOKEN_TYPES = [
        SemanticTokenTypes.Namespace,    # 0: Section names (geometry, basis, etc.)
        SemanticTokenTypes.Function,     # 1: Task operations
        SemanticTokenTypes.Variable,     # 2: Keywords
        SemanticTokenTypes.String,       # 3: String values (titles)
        SemanticTokenTypes.Number,       # 4: Numeric values
        SemanticTokenTypes.Keyword,      # 5: Reserved words (end, start)
        SemanticTokenTypes.Type,         # 6: Basis sets
        SemanticTokenTypes.Property,     # 7: DFT functionals
        SemanticTokenTypes.Class,        # 8: Elements
    ]

    # Token modifiers
    TOKEN_MODIFIERS = [
        SemanticTokenModifiers.Declaration,
        SemanticTokenModifiers.Readonly,
        SemanticTokenModifiers.Static,
        SemanticTokenModifiers.DefaultLibrary,
    ]

    # Section names (namespace type)
    SECTION_NAMES = {
        "geometry", "basis", "scf", "dft", "mp2", "ccsd", "ccsd(t)",
        "task", "property", "vib", "hessian", "tce", "mcscf", "ecp",
        "charge", "title", "start", "restart",
    }

    # Reserved keywords
    RESERVED_KEYWORDS = {"end", "start", "stop", "echo"}

    def __init__(self, server: LanguageServer):
        """Initialize the semantic tokens provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_legend(self) -> SemanticTokensLegend:
        """Get the semantic tokens legend.

        Returns:
            Semantic tokens legend
        """
        return SemanticTokensLegend(
            token_types=[t.value for t in self.TOKEN_TYPES],
            token_modifiers=[m.value for m in self.TOKEN_MODIFIERS],
        )

    def get_semantic_tokens(self, text: str) -> SemanticTokens:
        """Get semantic tokens for the document.

        Args:
            text: Document text

        Returns:
            Semantic tokens
        """
        data: List[int] = []
        lines = text.split("\n")
        prev_line = 0
        prev_char = 0

        for line_idx, line in enumerate(lines):
            tokens = self._tokenize_line(line, line_idx)

            for token in tokens:
                # Delta encoding
                if line_idx == prev_line:
                    delta_line = 0
                    delta_char = token[0] - prev_char
                else:
                    delta_line = line_idx - prev_line
                    delta_char = token[0]

                data.extend([delta_line, delta_char, token[1], token[2], token[3]])

                prev_line = line_idx
                prev_char = token[0]

        return SemanticTokens(data=data)

    def _tokenize_line(self, line: str, line_idx: int) -> List[tuple[int, int, int, int]]:
        """Tokenize a single line.

        Args:
            line: Line text
            line_idx: Line index

        Returns:
            List of (char_pos, length, token_type, token_modifiers)
        """
        tokens: List[tuple[int, int, int, int]] = []
        words = line.split()
        current_pos = 0

        for word in words:
            # Find word position (skip leading whitespace)
            while current_pos < len(line) and line[current_pos].isspace():
                current_pos += 1

            if current_pos >= len(line):
                break

            word_lower = word.lower()
            token_type: Optional[int] = None
            modifiers = 0

            # Check for section names
            if word_lower in self.SECTION_NAMES:
                token_type = 0  # namespace
                modifiers = 1  # declaration
            # Check for reserved keywords
            elif word_lower in self.RESERVED_KEYWORDS:
                token_type = 5  # keyword
            # Check for task operations
            elif word_lower in [op.lower() for op in TASK_OPERATIONS]:
                token_type = 1  # function
            # Check for basis sets
            elif any(word_lower == bs.lower() for bs in BASIS_SETS):
                token_type = 6  # type
            # Check for DFT functionals
            elif word_lower in [f.lower() for f in DFT_FUNCTIONALS]:
                token_type = 7  # property
            # Check for elements
            elif word_lower.capitalize() in ELEMENTS and len(word) <= 2:
                token_type = 8  # class
            # Check for numbers
            elif self._is_number(word):
                token_type = 4  # number

            if token_type is not None:
                tokens.append((current_pos, len(word), token_type, modifiers))

            current_pos += len(word)

        return tokens

    def _is_number(self, s: str) -> bool:
        """Check if a string represents a number.

        Args:
            s: String to check

        Returns:
            True if numeric
        """
        try:
            float(s)
            return True
        except ValueError:
            return False

    def get_semantic_tokens_range(
        self, text: str, range_: Range
    ) -> SemanticTokens:
        """Get semantic tokens for a specific range.

        Args:
            text: Document text
            range_: Range to get tokens for

        Returns:
            Semantic tokens for the range
        """
        lines = text.split("\n")
        start_line = range_.start.line
        end_line = min(range_.end.line, len(lines) - 1)

        range_text = "\n".join(lines[start_line : end_line + 1])
        return self.get_semantic_tokens(range_text)


def get_semantic_tokens_provider(server: LanguageServer) -> SemanticTokensProvider:
    """Create a semantic tokens provider instance.

    Args:
        server: The language server instance

    Returns:
        Semantic tokens provider instance
    """
    return SemanticTokensProvider(server)

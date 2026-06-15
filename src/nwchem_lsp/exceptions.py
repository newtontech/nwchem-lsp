"""Custom exceptions for NWChem LSP.

Wiki
----
- `wiki/synthesis/Parser_API.md`_ — Parser API exception reference
"""

from __future__ import annotations


class NWChemLSPError(Exception):
    """Base exception for all NWChem LSP errors."""

    def __init__(self, message: str = "An NWChem LSP error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class ParseError(NWChemLSPError):
    """Raised when parsing NWChem input fails."""

    def __init__(
        self, message: str = "Failed to parse NWChem input", line: int | None = None
    ) -> None:
        self.line = line
        super().__init__(message)


class ValidationError(NWChemLSPError):
    """Raised when NWChem input validation fails."""

    def __init__(
        self,
        message: str = "NWChem input validation failed",
        errors: list[dict[str, object]] | None = None,
    ) -> None:
        self.errors = errors or []
        super().__init__(message)


class ConfigurationError(NWChemLSPError):
    """Raised when LSP server configuration is invalid."""

    def __init__(self, message: str = "Invalid LSP server configuration") -> None:
        super().__init__(message)

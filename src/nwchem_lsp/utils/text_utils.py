"""Shared text utilities for NWChem LSP.

Centralises common text-manipulation helpers used across multiple modules.
"""

from __future__ import annotations


def get_word_at_position(line: str, column: int) -> str:
    """Extract the alphanumeric word at *column* within *line*.

    Scans left and right from *column* to find the boundaries of the
    contiguous alphanumeric run that contains the cursor position.

    Args:
        line: The source line.
        column: Zero-based character offset.

    Returns:
        The word string, or ``""`` when *line* is empty or *column* is
        out of range.
    """
    if not line or column < 0 or column > len(line):
        return ""

    start = column
    end = column

    while start > 0 and line[start - 1].isalnum():
        start -= 1

    while end < len(line) and line[end].isalnum():
        end += 1

    return line[start:end]

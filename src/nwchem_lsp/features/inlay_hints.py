"""LSP inlay hints provider for NWChem.

This module provides inlay hints for NWChem input files,
showing additional inline information like units and defaults.
"""

from typing import List, Optional

from lsprotocol.types import (
    InlayHint,
    InlayHintKind,
    Position,
)
from pygls.server import LanguageServer

from ..parser.nwchem_parser import NwchemParser


class InlayHintsProvider:
    """Provides inlay hints for NWChem input files."""

    # Units for geometry sections
    GEOMETRY_UNITS = {
        "angstroms": "Å",
        "angstrom": "Å",
        "bohr": "a₀",
        "nm": "nm",
        "pm": "pm",
    }

    # Section-specific hints
    SECTION_HINTS = {
        "geometry": [
            ("units", "units"),
            ("symmetry", "sym"),
            ("center", "center"),
        ],
        "dft": [
            ("xc", "functional"),
            ("grid", "grid quality"),
            ("convergence", "conv"),
        ],
        "basis": [
            ("spherical", "type"),
            ("cartesian", "type"),
        ],
        "scf": [
            ("thresh", "threshold"),
            ("maxiter", "max iter"),
        ],
    }

    def __init__(self, server: LanguageServer):
        """Initialize the inlay hints provider.

        Args:
            server: The language server instance
        """
        self.server = server

    def get_inlay_hints(
        self, text: str, start_line: int = 0, end_line: Optional[int] = None
    ) -> List[InlayHint]:
        """Get inlay hints for the document.

        Args:
            text: Document text
            start_line: Start line for hints
            end_line: End line for hints (None for all)

        Returns:
            List of inlay hints
        """
        hints: List[InlayHint] = []
        lines = text.split("\n")

        if end_line is None:
            end_line = len(lines)

        parser = NwchemParser(text)

        for line_idx in range(start_line, min(end_line, len(lines))):
            line = lines[line_idx].rstrip()
            if not line or line.strip().startswith("#"):
                continue

            line_hints = self._get_hints_for_line(line, line_idx, parser)
            hints.extend(line_hints)

        return hints

    def _get_hints_for_line(
        self, line: str, line_idx: int, parser: NwchemParser
    ) -> List[InlayHint]:
        """Get hints for a specific line.

        Args:
            line: Line text
            line_idx: Line index
            parser: NWChem parser instance

        Returns:
            List of inlay hints
        """
        hints: List[InlayHint] = []
        words = line.split()
        if not words:
            return hints

        first_word = words[0].lower()

        # Check if we're inside a geometry section
        current_section = self._get_current_section(parser, line_idx)

        # Add unit hints for geometry coordinates
        if current_section == "geometry" and len(words) >= 4:
            element = words[0].capitalize()
            if element in [
                "H",
                "He",
                "Li",
                "Be",
                "B",
                "C",
                "N",
                "O",
                "F",
                "Ne",
                "Na",
                "Mg",
                "Al",
                "Si",
                "P",
                "S",
                "Cl",
                "Ar",
                "K",
                "Ca",
                "Sc",
                "Ti",
                "V",
                "Cr",
                "Mn",
                "Fe",
            ]:
                # Check if coordinates look like numbers
                if self._is_coordinate_line(words):
                    # Add unit hint at end of line
                    hints.append(
                        InlayHint(
                            position=Position(line=line_idx, character=len(line)),
                            label="  // coordinates (Å)",
                            kind=InlayHintKind.Type,
                            padding_left=False,
                        )
                    )

        # Add hints for task lines
        if first_word == "task" and len(words) >= 2:
            theory = words[1].upper() if len(words) > 1 else ""
            operation = words[2].upper() if len(words) > 2 else "ENERGY"
            hints.append(
                InlayHint(
                    position=Position(line=line_idx, character=len(line)),
                    label=f"  // {theory} {operation}",
                    kind=InlayHintKind.Type,
                )
            )

        # Add hints for basis set library
        if first_word == "*" and "library" in line.lower():
            hints.append(
                InlayHint(
                    position=Position(line=line_idx, character=len(line)),
                    label="  // all atoms",
                    kind=InlayHintKind.Parameter,
                )
            )

        # Add hints for convergence thresholds
        if first_word in ("thresh", "tight", "tol") and len(words) > 1:
            hints.append(
                InlayHint(
                    position=Position(line=line_idx, character=len(line)),
                    label="  // convergence threshold",
                    kind=InlayHintKind.Type,
                )
            )

        # Add hints for charge
        if first_word == "charge" and len(words) > 1:
            try:
                charge_val = int(words[1])
                charge_desc = self._describe_charge(charge_val)
                hints.append(
                    InlayHint(
                        position=Position(line=line_idx, character=len(line)),
                        label=f"  // {charge_desc}",
                        kind=InlayHintKind.Type,
                    )
                )
            except ValueError:
                pass

        return hints

    def _get_current_section(self, parser: NwchemParser, line_idx: int) -> Optional[str]:
        """Get the current section at the given line.

        Args:
            parser: NWChem parser
            line_idx: Line index

        Returns:
            Section name or None
        """
        for section_name, sections in parser.sections.items():
            for section in sections:
                if section.start_line <= line_idx:
                    end = section.end_line if section.end_line is not None else float("inf")
                    if line_idx <= end:
                        return section_name
        return None

    def _is_coordinate_line(self, words: List[str]) -> bool:
        """Check if words represent a coordinate line.

        Args:
            words: Words on the line

        Returns:
            True if coordinates
        """
        if len(words) < 4:
            return False
        try:
            float(words[1])
            float(words[2])
            float(words[3])
            return True
        except ValueError:
            return False

    def _describe_charge(self, charge: int) -> str:
        """Get description for charge value.

        Args:
            charge: Charge value

        Returns:
            Description string
        """
        if charge == 0:
            return "neutral"
        elif charge > 0:
            return f"cation (+{charge})"
        else:
            return f"anion ({charge})"


def get_inlay_hints_provider(server: LanguageServer) -> InlayHintsProvider:
    """Create an inlay hints provider instance.

    Args:
        server: The language server instance

    Returns:
        Inlay hints provider instance
    """
    return InlayHintsProvider(server)

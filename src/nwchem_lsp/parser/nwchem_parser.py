"""NWChem input file parser.

This module provides parsing capabilities for NWChem input files (.nw),
including section identification, line context extraction, and completion
context determination.

This is the authoritative parser implementation. An orphaned TypeScript
parser exists at `src/parsers/nw.ts` for reference only -- it is deprecated
and not maintained. See the README "Parser Status" section for details.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParseContext:
    """Context information for a parsed NWChem file."""

    line_number: int
    column: int
    current_section: Optional[str]
    section_stack: List[str]
    line_content: str
    word_at_cursor: str
    is_in_block: bool


@dataclass
class NWchemSection:
    """Represents an NWChem input section."""

    name: str
    start_line: int
    end_line: Optional[int]
    keywords: List[str]
    content: List[str]
    line_start: int = 0  # Compatibility alias for start_line, set dynamically


@dataclass
class AtomCoordinate:
    """A single atom coordinate in a geometry block."""

    element: str
    x: float
    y: float
    z: float
    tag: Optional[str] = None


@dataclass
class GeometryBlock:
    """Parsed geometry block with units and atom coordinates."""

    units: str = "angstroms"
    coordinates: List[AtomCoordinate] = field(default_factory=list)


@dataclass
class BasisBlock:
    """Parsed basis block with library info and elements."""

    basis_set: str = ""
    library: bool = False
    elements: List[str] = field(default_factory=list)


@dataclass
class SCFBlock:
    """Parsed SCF block with calculation parameters."""

    maxiter: Optional[int] = None
    thresh: Optional[float] = None
    tol2e: Optional[float] = None
    direct: Optional[bool] = None
    vectors: Optional[str] = None


@dataclass
class TaskDirective:
    """A parsed task directive with theory and operation."""

    theory: str
    operation: str = "energy"


class NwchemParser:
    """Parser for NWChem input files."""

    SECTION_KEYWORDS = {
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

    TOP_LEVEL_KEYWORDS = {
        "start",
        "restart",
        "title",
        "echo",
        "set",
        "unset",
        "stop",
        "task",
        "charge",
        "memory",
        "permanent_dir",
        "scratch_dir",
        "print",
    }

    def __init__(self, source: str):
        """Initialize parser with source text."""
        self.source = source
        self.lines = source.splitlines()
        self.sections: Dict[str, List[NWchemSection]] = {}
        self._parse_sections()

    def _parse_sections(self) -> None:
        """Parse all sections from the source."""
        current_section: Optional[NWchemSection] = None
        section_keywords: List[str] = []
        section_content: List[str] = []

        for i, line in enumerate(self.lines):
            stripped = line.strip().lower()

            if not stripped or stripped.startswith("#"):
                if current_section:
                    section_content.append(line)
                continue

            parts = stripped.split()
            if parts[0] in self.SECTION_KEYWORDS:
                if current_section:
                    current_section.end_line = i - 1
                    current_section.content = section_content.copy()
                    current_section.keywords = section_keywords.copy()
                    if current_section.name not in self.sections:
                        self.sections[current_section.name] = []
                    self.sections[current_section.name].append(current_section)

                section_name = parts[0]
                section_keywords = []
                section_content = [line]
                current_section = NWchemSection(
                    name=section_name,
                    start_line=i,
                    end_line=None,
                    keywords=[],
                    content=[],
                )

            elif stripped == "end" and current_section:
                section_content.append(line)
                current_section.end_line = i
                current_section.content = section_content.copy()
                current_section.keywords = section_keywords.copy()
                if current_section.name not in self.sections:
                    self.sections[current_section.name] = []
                self.sections[current_section.name].append(current_section)
                current_section = None
                section_keywords = []
                section_content = []

            else:
                if current_section:
                    section_content.append(line)
                    if parts:
                        first_word = parts[0]
                        if not first_word.startswith("#"):
                            section_keywords.append(first_word)

        if current_section:
            current_section.end_line = len(self.lines) - 1
            current_section.content = section_content.copy()
            current_section.keywords = section_keywords.copy()
            if current_section.name not in self.sections:
                self.sections[current_section.name] = []
            self.sections[current_section.name].append(current_section)

    def get_section_at_line(self, line_number: int) -> Optional[str]:
        """Get the section name at a specific line number."""
        for section_name, sections in self.sections.items():
            for section in sections:
                end_line = section.end_line if section.end_line is not None else line_number
                if section.start_line <= line_number <= end_line:
                    return section_name
        return None

    def get_context(self, line_number: int, column: int) -> ParseContext:
        """Get parsing context at a specific position."""
        if line_number < 0 or line_number >= len(self.lines):
            return ParseContext(
                line_number=line_number,
                column=column,
                current_section=None,
                section_stack=[],
                line_content="",
                word_at_cursor="",
                is_in_block=False,
            )

        line_content = self.lines[line_number]
        current_section = self.get_section_at_line(line_number)
        section_stack: List[str] = []
        if current_section:
            section_stack.append(current_section)

        word_at_cursor = self._get_word_at_position(line_content, column)
        is_in_block = current_section is not None

        return ParseContext(
            line_number=line_number,
            column=column,
            current_section=current_section,
            section_stack=section_stack,
            line_content=line_content,
            word_at_cursor=word_at_cursor,
            is_in_block=is_in_block,
        )

    def _get_word_at_position(self, line: str, column: int) -> str:
        """Extract the word at a specific column position."""
        if not line or column < 0 or column > len(line):
            return ""

        start = column
        end = column

        while start > 0 and line[start - 1].isalnum():
            start -= 1

        while end < len(line) and line[end].isalnum():
            end += 1

        return line[start:end]

    def get_completion_context(self, line_number: int, column: int) -> Dict[str, Any]:
        """Get context information for completion requests."""
        context = self.get_context(line_number, column)
        line_content = context.line_content.lstrip().lower()

        completion_type = "top_level"

        if context.current_section:
            completion_type = context.current_section
        elif line_content.startswith("task"):
            completion_type = "task_operation"
        elif line_content.startswith("basis") or "library" in line_content:
            completion_type = "basis_set"
        elif line_content.startswith("dft") or line_content.startswith("xc"):
            completion_type = "dft_functional"

        return {
            "type": completion_type,
            "section": context.current_section,
            "word": context.word_at_cursor,
            "line": line_content,
            "in_block": context.is_in_block,
        }

    def get_all_sections(self) -> List[str]:
        """Get list of all section names."""
        return list(self.sections.keys())

    def get_section_content(self, section_name: str) -> List[NWchemSection]:
        """Get all instances of a section."""
        return self.sections.get(section_name, [])

    def is_valid_syntax(self) -> Tuple[bool, List[Tuple[int, str]]]:
        """Check if the input file has valid syntax."""
        errors: List[Tuple[int, str]] = []
        open_sections: List[Tuple[str, int]] = []

        for i, line in enumerate(self.lines):
            stripped = line.strip().lower()

            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if not parts:
                continue

            keyword = parts[0]

            if keyword in self.SECTION_KEYWORDS:
                open_sections.append((keyword, i))

            elif keyword == "end":
                if not open_sections:
                    errors.append((i, "Unexpected 'end' keyword (no matching section start)"))
                else:
                    open_sections.pop()

        for section_name, start_line in open_sections:
            errors.append((start_line, f"Unclosed section: '{section_name}'"))

        return len(errors) == 0, errors

    def parse(self) -> list[Any]:
        """Parse and return all sections as blocks."""
        blocks: list[Any] = []
        for section_name, sections in self.sections.items():
            for section in sections:
                # Add line_start attribute for compatibility
                if not hasattr(section, "line_start"):
                    section.line_start = section.start_line
                if not hasattr(section, "name"):
                    section.name = section_name
                blocks.append(section)

        for index, line in enumerate(self.lines):
            parts = line.strip().lower().split()
            if parts and parts[0] == "task":
                task = NWchemSection(
                    name="task",
                    start_line=index,
                    end_line=index,
                    keywords=parts[1:],
                    content=[line],
                )
                task.line_start = index + 1
                blocks.append(task)
        return blocks

    def validate(self) -> list[dict[str, Any]]:
        """Validate and return errors as list of dicts."""
        is_valid, errors = self.is_valid_syntax()
        result: list[dict[str, Any]] = []
        for line, message in errors:
            result.append({"line": line, "column": 0, "message": message})
        return result

    # --- Structured block parsers (parity with TypeScript nw.ts) ---

    def parse_task_directives(self) -> List[TaskDirective]:
        """Parse all task directives from the source.

        Returns a list of TaskDirective objects. When the operation is
        omitted, it defaults to 'energy', matching NWChem behaviour.
        """
        tasks: List[TaskDirective] = []
        for line in self.lines:
            stripped = line.strip().lower()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("task"):
                parts = stripped.split()
                if len(parts) >= 2:
                    tasks.append(
                        TaskDirective(
                            theory=parts[1],
                            operation=parts[2] if len(parts) >= 3 else "energy",
                        )
                    )
        return tasks

    def parse_geometry_block(self) -> Optional[GeometryBlock]:
        """Parse the first geometry block into a structured GeometryBlock.

        Returns None when no geometry section is present.
        """
        sections = self.sections.get("geometry")
        if not sections:
            return None

        section = sections[0]
        atoms: List[AtomCoordinate] = []
        units = "angstroms"

        for line in section.content:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#"):
                continue

            lower_line = trimmed.lower()

            # Units specification
            if "units" in lower_line:
                match = re.search(r"units\s+(\w+)", lower_line)
                if match:
                    units = match.group(1)
                continue

            # Skip end keyword and section header
            if lower_line == "end" or lower_line.startswith("end "):
                continue
            if lower_line == "geometry":
                continue

            # Parse atom coordinates: "C 0.0 0.0 0.0" or "C 0.0 0.0 0.0 tag"
            parts = trimmed.split()
            if len(parts) >= 4:
                element = parts[0]
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])
                    atoms.append(
                        AtomCoordinate(
                            element=element,
                            x=x,
                            y=y,
                            z=z,
                            tag=parts[4] if len(parts) > 4 else None,
                        )
                    )
                except ValueError:
                    continue

        return GeometryBlock(units=units, coordinates=atoms)

    def parse_basis_blocks(self) -> List[BasisBlock]:
        """Parse all basis blocks into structured BasisBlock objects.

        Returns an empty list when no basis section is present.
        """
        sections = self.sections.get("basis")
        if not sections:
            return []

        result: List[BasisBlock] = []
        for section in sections:
            elements: List[str] = []
            basis_set = ""
            library = False

            for line in section.content:
                trimmed = line.strip()
                if not trimmed or trimmed.startswith("#"):
                    continue

                lower_line = trimmed.lower()
                if lower_line == "end" or lower_line.startswith("end "):
                    continue

                # Check for library keyword
                if "library" in lower_line:
                    library = True
                    match = re.search(r"library\s+(\S+)", lower_line)
                    if match:
                        basis_set = match.group(1)

                # Parse element specifications (1-2 letter element symbols)
                parts = trimmed.split()
                if parts and re.match(r"^[A-Za-z]{1,2}$", parts[0]):
                    elements.append(parts[0])

            result.append(
                BasisBlock(basis_set=basis_set, library=library, elements=elements)
            )
        return result

    def parse_scf_block(self) -> Optional[SCFBlock]:
        """Parse the first SCF block into a structured SCFBlock.

        Returns None when no SCF section is present.
        """
        sections = self.sections.get("scf")
        if not sections:
            return None

        section = sections[0]
        scf = SCFBlock()

        for line in section.content:
            trimmed = line.strip().lower()
            if not trimmed or trimmed.startswith("#") or trimmed == "end":
                continue

            if trimmed.startswith("maxiter"):
                match = re.search(r"maxiter\s+(\d+)", trimmed)
                if match:
                    scf.maxiter = int(match.group(1))

            if trimmed.startswith("thresh"):
                match = re.search(r"thresh\s+([\d.eE+-]+)", trimmed)
                if match:
                    scf.thresh = float(match.group(1))

            if trimmed.startswith("tol2e"):
                match = re.search(r"tol2e\s+([\d.eE+-]+)", trimmed)
                if match:
                    scf.tol2e = float(match.group(1))

            if trimmed.startswith("direct"):
                scf.direct = True

            if trimmed.startswith("vectors"):
                match = re.search(r"vectors\s+(.+)", trimmed)
                if match:
                    scf.vectors = match.group(1).strip()

        return scf


def parse_nwchem_source(source: str) -> NwchemParser:
    """Parse NWChem input source."""
    return NwchemParser(source)


def get_line_keywords(line: str) -> List[str]:
    """Extract keywords from a line."""
    stripped = line.strip().lower()
    if not stripped or stripped.startswith("#"):
        return []

    parts = stripped.split()
    return parts

"""Parser parity tests.

Validates that the Python parser (authoritative) matches the capabilities
tested in the TypeScript parser test suite (tests/parsers/nw.test.ts).
These tests ensure behavioral alignment documented in PARITY.md.
"""

import pytest

from nwchem_lsp.parser.nwchem_parser import (
    AtomCoordinate,
    BasisBlock,
    GeometryBlock,
    NWchemSection,
    NwchemParser,
    SCFBlock,
    TaskDirective,
    get_line_keywords,
    parse_nwchem_source,
)


# ---------------------------------------------------------------------------
# Task Directive Parsing (mirrors TS: Task Directive Parsing)
# ---------------------------------------------------------------------------


class TestTaskDirectiveParsing:
    """Parity with TypeScript parseTaskDirectives() tests."""

    def test_single_task_directive(self) -> None:
        """Python should identify a single task directive."""
        source = "task scf energy"
        parser = NwchemParser(source)
        blocks = parser.parse()
        task_blocks = [b for b in blocks if b.name == "task"]
        assert len(task_blocks) == 1
        assert task_blocks[0].keywords == ["scf", "energy"]

    def test_multiple_task_directives(self) -> None:
        """Python should identify multiple task directives."""
        source = "task scf energy\ntask dft optimize\ntask mp2 frequency"
        parser = NwchemParser(source)
        blocks = parser.parse()
        task_blocks = [b for b in blocks if b.name == "task"]
        assert len(task_blocks) == 3
        assert task_blocks[0].keywords == ["scf", "energy"]
        assert task_blocks[1].keywords == ["dft", "optimize"]
        assert task_blocks[2].keywords == ["mp2", "frequency"]

    def test_task_default_operation(self) -> None:
        """Python task with no operation should have only theory in keywords."""
        source = "task scf"
        parser = NwchemParser(source)
        blocks = parser.parse()
        task_blocks = [b for b in blocks if b.name == "task"]
        assert len(task_blocks) == 1
        assert task_blocks[0].keywords == ["scf"]

    def test_task_directive_ignores_comments(self) -> None:
        """Task parsing should skip comment lines."""
        source = "# Task directive\ntask scf energy"
        parser = NwchemParser(source)
        blocks = parser.parse()
        task_blocks = [b for b in blocks if b.name == "task"]
        assert len(task_blocks) == 1

    def test_task_inside_section_not_double_counted(self) -> None:
        """Task directives inside sections should still be found by parse()."""
        source = "geometry\n  H 0.0 0.0 0.0\nend\ntask scf energy"
        parser = NwchemParser(source)
        blocks = parser.parse()
        task_blocks = [b for b in blocks if b.name == "task"]
        assert len(task_blocks) == 1
        assert task_blocks[0].keywords == ["scf", "energy"]


# ---------------------------------------------------------------------------
# Structured TaskDirective parsing (mirrors TS parseTaskDirectives return)
# ---------------------------------------------------------------------------


class TestStructuredTaskDirectives:
    """Test the parse_task_directives() method returning TaskDirective objects."""

    def test_single_task(self) -> None:
        """Should return one TaskDirective with theory and operation."""
        source = "task scf energy"
        parser = NwchemParser(source)
        tasks = parser.parse_task_directives()
        assert len(tasks) == 1
        assert tasks[0].theory == "scf"
        assert tasks[0].operation == "energy"

    def test_multiple_tasks(self) -> None:
        """Should return multiple TaskDirectives."""
        source = "task scf energy\ntask dft optimize\ntask mp2 frequency"
        parser = NwchemParser(source)
        tasks = parser.parse_task_directives()
        assert len(tasks) == 3
        assert tasks[0] == TaskDirective(theory="scf", operation="energy")
        assert tasks[1] == TaskDirective(theory="dft", operation="optimize")
        assert tasks[2] == TaskDirective(theory="mp2", operation="frequency")

    def test_default_operation_is_energy(self) -> None:
        """Task with no operation should default to 'energy'."""
        source = "task scf"
        parser = NwchemParser(source)
        tasks = parser.parse_task_directives()
        assert len(tasks) == 1
        assert tasks[0].operation == "energy"

    def test_ignores_comments(self) -> None:
        """Comment lines should not produce task directives."""
        source = "# Task directive\ntask scf energy"
        parser = NwchemParser(source)
        tasks = parser.parse_task_directives()
        assert len(tasks) == 1

    def test_empty_source_no_tasks(self) -> None:
        """Empty source should produce no task directives."""
        parser = NwchemParser("")
        assert parser.parse_task_directives() == []


# ---------------------------------------------------------------------------
# Section Parsing (mirrors TS: Section Management)
# ---------------------------------------------------------------------------


class TestSectionParsing:
    """Parity with TypeScript section management tests."""

    def test_parse_empty_source(self) -> None:
        """Empty source should have no sections."""
        parser = NwchemParser("")
        assert parser.get_all_sections() == []

    def test_parse_source_with_only_comments(self) -> None:
        """Comment-only source should have no sections."""
        source = "# This is a comment\n# Another comment"
        parser = NwchemParser(source)
        assert parser.get_all_sections() == []

    def test_get_all_sections(self) -> None:
        """Should list all section names."""
        source = "geometry\nend\nbasis\nend\nscf\nend"
        parser = NwchemParser(source)
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "scf" in sections

    def test_get_section_content(self) -> None:
        """Should return section content instances."""
        source = "geometry\n  C 0.0 0.0 0.0\nend"
        parser = NwchemParser(source)
        sections = parser.get_section_content("geometry")
        assert len(sections) == 1
        assert sections[0].name == "geometry"

    def test_get_section_at_line(self) -> None:
        """Should identify section at specific lines."""
        source = "geometry\n  C 0.0 0.0 0.0\nend"
        parser = NwchemParser(source)
        assert parser.get_section_at_line(0) == "geometry"
        assert parser.get_section_at_line(1) == "geometry"
        assert parser.get_section_at_line(2) == "geometry"
        assert parser.get_section_at_line(10) is None

    def test_multiple_sections(self) -> None:
        """Should parse multiple distinct sections."""
        source = "geometry\n  H 0.0 0.0 0.0\nend\n\nbasis\n  H library 6-31g\nend"
        parser = NwchemParser(source)
        assert "geometry" in parser.sections
        assert "basis" in parser.sections
        assert len(parser.sections["geometry"]) == 1
        assert len(parser.sections["basis"]) == 1

    def test_section_content_contains_lines(self) -> None:
        """Section content should include inner lines."""
        source = "geometry\n  C 0.0 0.0 0.0\n  H 1.0 0.0 0.0\nend"
        parser = NwchemParser(source)
        section = parser.get_section_content("geometry")[0]
        assert len(section.content) >= 2


# ---------------------------------------------------------------------------
# Structured GeometryBlock parsing (mirrors TS parseGeometryBlock)
# ---------------------------------------------------------------------------


class TestGeometryBlockParsing:
    """Parity with TypeScript parseGeometryBlock() tests."""

    def test_geometry_with_atoms(self) -> None:
        """Should parse atoms into AtomCoordinate objects."""
        source = "geometry\n  C 0.0 0.0 0.0\n  H 1.0 0.0 0.0\n  H 0.0 1.0 0.0\n  H 0.0 0.0 1.0\nend"
        parser = NwchemParser(source)
        geometry = parser.parse_geometry_block()
        assert geometry is not None
        assert geometry.units == "angstroms"
        assert len(geometry.coordinates) == 4
        assert geometry.coordinates[0].element == "C"
        assert geometry.coordinates[0].x == 0.0
        assert geometry.coordinates[0].y == 0.0
        assert geometry.coordinates[0].z == 0.0

    def test_geometry_with_units_bohr(self) -> None:
        """Should parse units specification."""
        source = "geometry\n  units bohr\n  H 0.0 0.0 0.0\nend"
        parser = NwchemParser(source)
        geometry = parser.parse_geometry_block()
        assert geometry is not None
        assert geometry.units == "bohr"
        assert len(geometry.coordinates) == 1

    def test_geometry_with_atom_tags(self) -> None:
        """Should parse atom tags."""
        source = "geometry\n  C 0.0 0.0 0.0 carbon1\n  O 1.2 0.0 0.0 oxygen1\nend"
        parser = NwchemParser(source)
        geometry = parser.parse_geometry_block()
        assert geometry is not None
        assert geometry.coordinates[0].tag == "carbon1"
        assert geometry.coordinates[1].tag == "oxygen1"

    def test_no_geometry_returns_none(self) -> None:
        """No geometry block should return None."""
        parser = NwchemParser("start molecule")
        assert parser.parse_geometry_block() is None


# ---------------------------------------------------------------------------
# Structured BasisBlock parsing (mirrors TS parseBasisBlock)
# ---------------------------------------------------------------------------


class TestBasisBlockParsing:
    """Parity with TypeScript parseBasisBlock() tests."""

    def test_basis_with_library(self) -> None:
        """Should parse library basis set."""
        source = "basis\n  * library 6-31g*\nend"
        parser = NwchemParser(source)
        blocks = parser.parse_basis_blocks()
        assert len(blocks) == 1
        assert blocks[0].basis_set == "6-31g*"
        assert blocks[0].library is True

    def test_basis_with_explicit_elements(self) -> None:
        """Should parse element specifications."""
        source = "basis\n  C library cc-pvdz\n  H library cc-pvdz\nend"
        parser = NwchemParser(source)
        blocks = parser.parse_basis_blocks()
        assert len(blocks) == 1
        assert "C" in blocks[0].elements
        assert "H" in blocks[0].elements

    def test_no_basis_returns_empty(self) -> None:
        """No basis block should return empty list."""
        parser = NwchemParser("geometry\nend")
        assert parser.parse_basis_blocks() == []


# ---------------------------------------------------------------------------
# Structured SCFBlock parsing (mirrors TS parseSCFBlock)
# ---------------------------------------------------------------------------


class TestSCFBlockParsing:
    """Parity with TypeScript parseSCFBlock() tests."""

    def test_scf_maxiter(self) -> None:
        """Should parse maxiter."""
        source = "scf\n  maxiter 50\nend"
        parser = NwchemParser(source)
        scf = parser.parse_scf_block()
        assert scf is not None
        assert scf.maxiter == 50

    def test_scf_thresh(self) -> None:
        """Should parse thresh."""
        source = "scf\n  thresh 1e-6\nend"
        parser = NwchemParser(source)
        scf = parser.parse_scf_block()
        assert scf is not None
        assert scf.thresh == 1e-6

    def test_scf_tol2e(self) -> None:
        """Should parse tol2e."""
        source = "scf\n  tol2e 1e-8\nend"
        parser = NwchemParser(source)
        scf = parser.parse_scf_block()
        assert scf is not None
        assert scf.tol2e == 1e-8

    def test_scf_direct(self) -> None:
        """Should parse direct flag."""
        source = "scf\n  direct\nend"
        parser = NwchemParser(source)
        scf = parser.parse_scf_block()
        assert scf is not None
        assert scf.direct is True

    def test_scf_vectors(self) -> None:
        """Should parse vectors."""
        source = "scf\n  vectors input atomic\nend"
        parser = NwchemParser(source)
        scf = parser.parse_scf_block()
        assert scf is not None
        assert scf.vectors == "input atomic"

    def test_scf_complete_block(self) -> None:
        """Should parse all SCF parameters together."""
        source = "scf\n  maxiter 100\n  thresh 1e-7\n  tol2e 1e-9\n  direct\n  vectors input atomic\nend"
        parser = NwchemParser(source)
        scf = parser.parse_scf_block()
        assert scf is not None
        assert scf.maxiter == 100
        assert scf.thresh == 1e-7
        assert scf.tol2e == 1e-9
        assert scf.direct is True
        assert scf.vectors == "input atomic"

    def test_no_scf_returns_none(self) -> None:
        """No SCF block should return None."""
        parser = NwchemParser("geometry\nend")
        assert parser.parse_scf_block() is None


# ---------------------------------------------------------------------------
# Syntax validation (mirrors TS: Syntax Validation)
# ---------------------------------------------------------------------------


class TestSyntaxValidation:
    """Parity with TypeScript isValidSyntax() tests."""

    def test_valid_syntax(self) -> None:
        """Correctly closed sections should validate."""
        source = "geometry\nend"
        parser = NwchemParser(source)
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid is True
        assert len(errors) == 0

    def test_unclosed_section(self) -> None:
        """Unclosed sections should be detected."""
        source = "geometry\n  C 0.0 0.0 0.0"
        parser = NwchemParser(source)
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid is False
        assert len(errors) == 1
        assert "Unclosed" in errors[0][1]

    def test_unexpected_end(self) -> None:
        """Unexpected end keyword should be detected."""
        source = "end"
        parser = NwchemParser(source)
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid is False
        assert len(errors) == 1
        assert "Unexpected" in errors[0][1]


# ---------------------------------------------------------------------------
# Context parsing (mirrors TS: Context Parsing)
# ---------------------------------------------------------------------------


class TestContextParsing:
    """Parity with TypeScript getContext() and getCompletionContext() tests."""

    def test_context_at_position(self) -> None:
        """Should return correct context at a given position."""
        source = "geometry\n  C 0.0 0.0 0.0\nend"
        parser = NwchemParser(source)
        context = parser.get_context(1, 5)
        assert context.current_section == "geometry"
        assert context.line_content == "  C 0.0 0.0 0.0"
        assert context.is_in_block is True

    def test_word_at_cursor(self) -> None:
        """Should extract word at cursor position."""
        source = "start water"
        parser = NwchemParser(source)
        context = parser.get_context(0, 8)
        assert context.word_at_cursor == "water"

    def test_completion_context_task(self) -> None:
        """Task line should give task_operation completion type."""
        source = "task scf"
        parser = NwchemParser(source)
        completion = parser.get_completion_context(0, 8)
        assert completion["type"] == "task_operation"
        assert completion["section"] is None


# ---------------------------------------------------------------------------
# Edge cases and line keywords
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Parity with TypeScript getLineKeywords() and edge cases."""

    def test_get_line_keywords(self) -> None:
        """Should split line into keywords."""
        assert get_line_keywords("start molecule") == ["start", "molecule"]
        assert get_line_keywords("  # comment") == []
        assert get_line_keywords("") == []

    def test_parse_nwchem_source_convenience(self) -> None:
        """parse_nwchem_source should return a NwchemParser instance."""
        parser = parse_nwchem_source("geometry\nend")
        assert isinstance(parser, NwchemParser)

    def test_validate_method(self) -> None:
        """validate() should return list of dicts."""
        source = "geometry\n  C 0.0 0.0 0.0"
        parser = NwchemParser(source)
        errors = parser.validate()
        assert isinstance(errors, list)
        assert len(errors) == 1
        assert "line" in errors[0]
        assert "column" in errors[0]
        assert "message" in errors[0]

    def test_full_input_file_parsing(self) -> None:
        """Complete NWChem input file should parse all sections + tasks."""
        source = """start water

title "Water molecule"

geometry
  O 0.0 0.0 0.0
  H 0.757 0.586 0.0
  H -0.757 0.586 0.0
end

basis
  * library 6-31g*
end

scf
  maxiter 50
  thresh 1e-6
end

task scf energy"""
        parser = NwchemParser(source)

        # Check sections
        sections = parser.get_all_sections()
        assert "geometry" in sections
        assert "basis" in sections
        assert "scf" in sections

        # Check structured geometry
        geometry = parser.parse_geometry_block()
        assert geometry is not None
        assert len(geometry.coordinates) == 3

        # Check structured basis
        basis = parser.parse_basis_blocks()
        assert len(basis) == 1
        assert basis[0].library is True

        # Check structured SCF
        scf = parser.parse_scf_block()
        assert scf is not None
        assert scf.maxiter == 50

        # Check task directives
        tasks = parser.parse_task_directives()
        assert len(tasks) == 1
        assert tasks[0].theory == "scf"
        assert tasks[0].operation == "energy"

        # Check syntax validity
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid is True

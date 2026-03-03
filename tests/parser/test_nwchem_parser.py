"""Tests for the NWChem parser module."""

import pytest

from nwchem_lsp.parser.nwchem_parser import (
    NwchemParser,
    NWchemSection,
    ParseContext,
    parse_nwchem_source,
    get_line_keywords,
)


class TestParseContext:
    """Test ParseContext dataclass."""

    def test_parse_context_creation(self):
        """Test creating a ParseContext object."""
        context = ParseContext(
            line_number=5,
            column=10,
            current_section="geometry",
            section_stack=["geometry"],
            line_content="H 0.0 0.0 0.0",
            word_at_cursor="H",
            is_in_block=True,
        )
        assert context.line_number == 5
        assert context.column == 10
        assert context.current_section == "geometry"
        assert context.section_stack == ["geometry"]
        assert context.line_content == "H 0.0 0.0 0.0"
        assert context.word_at_cursor == "H"
        assert context.is_in_block is True


class TestNWchemSection:
    """Test NWchemSection dataclass."""

    def test_section_creation(self):
        """Test creating a section."""
        section = NWchemSection(
            name="geometry",
            start_line=0,
            end_line=5,
            keywords=["units", "angstroms"],
            content=["geometry", "H 0 0 0", "end"],
        )
        assert section.name == "geometry"
        assert section.start_line == 0
        assert section.end_line == 5
        assert section.keywords == ["units", "angstroms"]
        assert len(section.content) == 3


class TestNwchemParser:
    """Test NwchemParser class."""

    def test_parse_simple_geometry(self):
        """Test parsing a simple geometry section."""
        source = """geometry
  H 0.0 0.0 0.0
  O 0.0 0.0 1.0
end"""
        parser = NwchemParser(source)
        assert "geometry" in parser.sections
        sections = parser.sections["geometry"]
        assert len(sections) == 1
        assert sections[0].name == "geometry"
        assert sections[0].start_line == 0
        assert sections[0].end_line == 3

    def test_parse_multiple_sections(self):
        """Test parsing multiple sections."""
        source = """geometry
  H 0.0 0.0 0.0
end

basis
  H library 6-31g
end"""
        parser = NwchemParser(source)
        assert "geometry" in parser.sections
        assert "basis" in parser.sections
        assert len(parser.sections["geometry"]) == 1
        assert len(parser.sections["basis"]) == 1

    def test_get_section_at_line(self):
        """Test getting section at a specific line."""
        source = """geometry
  H 0.0 0.0 0.0
end

basis
  H library 6-31g
end"""
        parser = NwchemParser(source)
        assert parser.get_section_at_line(1) == "geometry"
        assert parser.get_section_at_line(4) == "basis"
        assert parser.get_section_at_line(10) is None

    def test_get_context(self):
        """Test getting parse context."""
        source = """geometry
  H 0.0 0.0 0.0
end"""
        parser = NwchemParser(source)
        context = parser.get_context(1, 2)
        assert context.line_number == 1
        assert context.line_content == "  H 0.0 0.0 0.0"
        assert context.current_section == "geometry"
        assert context.is_in_block is True

    def test_get_word_at_position(self):
        """Test word extraction at position."""
        parser = NwchemParser("")
        word = parser._get_word_at_position("H 0.0 0.0 0.0", 0)
        assert word == "H"
        word = parser._get_word_at_position("H 0.0 0.0 0.0", 2)
        assert word == "0"
        word = parser._get_word_at_position("", 0)
        assert word == ""

    def test_is_valid_syntax_valid(self):
        """Test valid syntax check."""
        source = """geometry
  H 0.0 0.0 0.0
end"""
        parser = NwchemParser(source)
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid is True
        assert len(errors) == 0

    def test_is_valid_syntax_unclosed(self):
        """Test unclosed section detection."""
        source = """geometry
  H 0.0 0.0 0.0"""
        parser = NwchemParser(source)
        is_valid, errors = parser.is_valid_syntax()
        assert is_valid is False
        assert len(errors) == 1
        assert "Unclosed" in errors[0][1]


class TestParseNwchemSource:
    """Test parse_nwchem_source function."""

    def test_function_exists(self):
        """Test that function exists."""
        source = "geometry\nend"
        parser = parse_nwchem_source(source)
        assert isinstance(parser, NwchemParser)

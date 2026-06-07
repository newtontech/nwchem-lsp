"""Tests for definition provider."""

import pytest
from lsprotocol.types import Position

from nwchem_lsp.features.definition import DefinitionProvider, get_definition_provider


class TestDefinitionProvider:
    """Test suite for DefinitionProvider."""

    @pytest.fixture
    def provider(self):
        """Create a definition provider for testing."""
        return DefinitionProvider()

    def test_provider_exists(self):
        """Test that provider can be instantiated."""
        provider = DefinitionProvider()
        assert provider is not None

    def test_factory_function(self):
        """Test that factory function works."""
        provider = get_definition_provider()
        assert provider is not None
        assert isinstance(provider, DefinitionProvider)

    def test_get_definition_empty_source(self, provider):
        """Test definition on empty source."""
        result = provider.get_definition("", Position(line=0, character=0))
        assert result is None

    def test_get_definition_out_of_range(self, provider):
        """Test definition on position out of range."""
        source = "geometry\n  O 0 0 0\nend"
        result = provider.get_definition(source, Position(line=100, character=0))
        assert result is None

    def test_get_definition_on_end(self, provider):
        """Test jumping from 'end' to section start."""
        source = """geometry
  O 0 0 0
end"""
        result = provider.get_definition(source, Position(line=2, character=0))
        assert result is not None
        assert result.range.start.line == 0
        assert result.range.start.character == 0

    def test_get_definition_on_end_with_indentation(self, provider):
        """Test jumping from indented 'end' to section start."""
        source = """geometry
  O 0 0 0
  end"""
        result = provider.get_definition(source, Position(line=2, character=2))
        assert result is not None
        assert result.range.start.line == 0

    def test_get_definition_nested_sections(self, provider):
        """Test jumping from 'end' with nested sections."""
        source = """geometry
  O 0 0 0
end

basis
  * library sto-3g
end"""
        # Jump from second end (line 6)
        result = provider.get_definition(source, Position(line=6, character=0))
        assert result is not None
        assert result.range.start.line == 4  # Should jump to 'basis'

    def test_get_definition_no_matching_section(self, provider):
        """Test jumping from 'end' with no matching section."""
        source = """end"""
        result = provider.get_definition(source, Position(line=0, character=0))
        assert result is None

    def test_get_word_at_position(self, provider):
        """Test word extraction at position."""
        line = "geometry units angstroms"
        word = provider._get_word_at_position(line, 0)
        assert word == "geometry"

    def test_get_word_at_position_middle(self, provider):
        """Test word extraction in middle of word."""
        line = "geometry units angstroms"
        word = provider._get_word_at_position(line, 3)
        assert word == "geometry"

    def test_get_word_at_position_empty_line(self, provider):
        """Test word extraction on empty line."""
        word = provider._get_word_at_position("", 0)
        assert word == ""

    def test_find_section_start_simple(self, provider):
        """Test finding section start for simple case."""
        source = """geometry
  O 0 0 0
end"""
        result = provider._find_section_start(source, 2)
        assert result is not None
        assert result.range.start.line == 0

    def test_find_section_start_multiple_sections(self, provider):
        """Test finding section start with multiple sections."""
        source = """geometry
  O 0 0 0
end

basis
  * library sto-3g
end"""
        # Find start for second 'end'
        result = provider._find_section_start(source, 5)
        assert result is not None
        assert result.range.start.line == 4

    def test_find_section_start_by_type(self, provider):
        """Test finding section start by type."""
        source = """geometry
  O 0 0 0
end

basis
  * library sto-3g
end"""
        result = provider._find_section_start_by_type(source, "basis", 5)
        assert result is not None
        assert result.range.start.line == 4


class TestDefinitionEdgeCases:
    """Test edge cases for definition provider."""

    @pytest.fixture
    def provider(self):
        """Create a definition provider for testing."""
        return DefinitionProvider()

    def test_empty_sections_stack(self, provider):
        """Test behavior with empty sections stack."""
        source = """# Just comments
# No sections"""
        result = provider._find_section_start(source, 1)
        assert result is None

    def test_only_comments(self, provider):
        """Test with only comments."""
        source = """# Comment 1
# Comment 2"""
        result = provider.get_definition(source, Position(line=0, character=0))
        assert result is None

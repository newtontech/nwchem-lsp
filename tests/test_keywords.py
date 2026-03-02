"""Tests for the keywords module."""

import pytest

from nwchem_lsp.data.keywords import (
    ELEMENTS,
    KEYWORDS,
    TASK_OPERATIONS,
    TASK_THEORIES,
    TOP_LEVEL_SECTIONS,
    KeywordInfo,
    get_all_keyword_names,
    get_keyword_info,
    get_keywords_by_section,
    is_section_block,
    is_valid_keyword,
)


class TestKeywordInfo:
    """Test KeywordInfo dataclass."""

    def test_keyword_info_creation(self):
        """Test creating a KeywordInfo object."""
        kw = KeywordInfo(
            name="test",
            description="A test keyword",
            section="top",
        )
        assert kw.name == "test"
        assert kw.description == "A test keyword"
        assert kw.section == "top"
        assert kw.args == []
        assert kw.optional_args == []
        assert kw.requires_block is False

    def test_keyword_info_with_args(self):
        """Test KeywordInfo with arguments."""
        kw = KeywordInfo(
            name="task",
            description="Task directive",
            section="top",
            args=["theory", "operation"],
            optional_args=["options"],
            requires_block=False,
        )
        assert kw.args == ["theory", "operation"]
        assert kw.optional_args == ["options"]


class TestGetKeywordInfo:
    """Test get_keyword_info function."""

    def test_get_existing_keyword(self):
        """Test getting info for an existing keyword."""
        info = get_keyword_info("geometry")
        assert info is not None
        assert info.name == "geometry"
        assert info.requires_block is True

    def test_get_keyword_case_insensitive(self):
        """Test that keyword lookup is case insensitive."""
        info_lower = get_keyword_info("geometry")
        info_upper = get_keyword_info("GEOMETRY")
        info_mixed = get_keyword_info("Geometry")
        assert info_lower == info_upper == info_mixed

    def test_get_nonexistent_keyword(self):
        """Test getting info for a non-existent keyword."""
        info = get_keyword_info("nonexistent")
        assert info is None


class TestIsValidKeyword:
    """Test is_valid_keyword function."""

    def test_valid_keyword(self):
        """Test checking a valid keyword."""
        assert is_valid_keyword("geometry") is True
        assert is_valid_keyword("scf") is True
        assert is_valid_keyword("dft") is True

    def test_invalid_keyword(self):
        """Test checking an invalid keyword."""
        assert is_valid_keyword("invalid") is False

    def test_case_insensitive(self):
        """Test that validation is case insensitive."""
        assert is_valid_keyword("GEOMETRY") is True
        assert is_valid_keyword("Geometry") is True


class TestIsSectionBlock:
    """Test is_section_block function."""

    def test_block_keyword(self):
        """Test that block keywords are identified."""
        assert is_section_block("geometry") is True
        assert is_section_block("basis") is True
        assert is_section_block("scf") is True
        assert is_section_block("dft") is True

    def test_non_block_keyword(self):
        """Test that non-block keywords return False."""
        assert is_section_block("task") is False
        assert is_section_block("charge") is False
        assert is_section_block("start") is False


class TestGetKeywordsBySection:
    """Test get_keywords_by_section function."""

    def test_get_geometry_keywords(self):
        """Test getting geometry section keywords."""
        keywords = get_keywords_by_section("geometry")
        assert len(keywords) > 0
        names = [kw.name for kw in keywords]
        assert "angstroms" in names
        assert "au" in names

    def test_get_scf_keywords(self):
        """Test getting SCF section keywords."""
        keywords = get_keywords_by_section("scf")
        assert len(keywords) > 0
        names = [kw.name for kw in keywords]
        assert "rhf" in names
        assert "uhf" in names


class TestGetAllKeywordNames:
    """Test get_all_keyword_names function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        names = get_all_keyword_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_contains_expected_keywords(self):
        """Test that expected keywords are in the list."""
        names = get_all_keyword_names()
        assert "geometry" in names
        assert "basis" in names
        assert "scf" in names
        assert "dft" in names


class TestConstants:
    """Test module constants."""

    def test_top_level_sections(self):
        """Test TOP_LEVEL_SECTIONS constant."""
        assert isinstance(TOP_LEVEL_SECTIONS, list)
        assert "geometry" in TOP_LEVEL_SECTIONS
        assert "basis" in TOP_LEVEL_SECTIONS
        assert "scf" in TOP_LEVEL_SECTIONS

    def test_task_theories(self):
        """Test TASK_THEORIES constant."""
        assert isinstance(TASK_THEORIES, list)
        assert "scf" in TASK_THEORIES
        assert "dft" in TASK_THEORIES
        assert "mp2" in TASK_THEORIES

    def test_task_operations(self):
        """Test TASK_OPERATIONS constant."""
        assert isinstance(TASK_OPERATIONS, list)
        assert "energy" in TASK_OPERATIONS
        assert "optimize" in TASK_OPERATIONS
        assert "frequencies" in TASK_OPERATIONS

    def test_elements(self):
        """Test ELEMENTS constant."""
        assert isinstance(ELEMENTS, list)
        assert "H" in ELEMENTS
        assert "C" in ELEMENTS
        assert "O" in ELEMENTS
        assert "Fe" in ELEMENTS


class TestKeywordDatabase:
    """Test the KEYWORDS database."""

    def test_keywords_dict(self):
        """Test that KEYWORDS is a valid dictionary."""
        assert isinstance(KEYWORDS, dict)
        assert len(KEYWORDS) > 0

    def test_keyword_values_are_keywordinfo(self):
        """Test that all values are KeywordInfo objects."""
        for kw in KEYWORDS.values():
            assert isinstance(kw, KeywordInfo)

    def test_geometry_keyword(self):
        """Test geometry keyword definition."""
        kw = KEYWORDS["geometry"]
        assert kw.name == "geometry"
        assert kw.requires_block is True
        assert kw.section == "top"

    def test_scf_keyword(self):
        """Test scf keyword definition."""
        kw = KEYWORDS["scf"]
        assert kw.name == "scf"
        assert kw.requires_block is True
        assert kw.section == "top"

    def test_task_keyword(self):
        """Test task keyword definition."""
        kw = KEYWORDS["task"]
        assert kw.name == "task"
        assert kw.requires_block is False
        assert "theory" in kw.args
        assert "operation" in kw.args

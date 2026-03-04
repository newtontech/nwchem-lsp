"""Tests for folding range provider."""

import pytest

from nwchem_lsp.features.folding_range import FoldingRangeProvider, get_folding_range_provider


class TestFoldingRangeProvider:
    """Test folding range provider."""

    @pytest.fixture
    def provider(self):
        """Create a folding range provider."""
        return get_folding_range_provider()

    def test_get_folding_ranges_geometry(self, provider):
        """Test folding ranges for geometry section."""
        text = """start test

geometry units angstroms
  O  0.000  0.000  0.000
  H  0.000  0.790  0.580
end

task dft optimize
"""
        ranges = provider.get_folding_ranges(text)
        assert len(ranges) == 1
        assert ranges[0].start_line == 2
        assert ranges[0].end_line == 5
        assert ranges[0].collapsed_text == "geometry ... end"

    def test_get_folding_ranges_multiple_sections(self, provider):
        """Test folding ranges for multiple sections."""
        text = """start test

geometry units angstroms
  O  0.000  0.000  0.000
end

basis spherical
  * library 6-31G*
end

dft
  xc b3lyp
end
"""
        ranges = provider.get_folding_ranges(text)
        assert len(ranges) == 3
        assert ranges[0].start_line == 2
        assert ranges[1].start_line == 6
        assert ranges[2].start_line == 10

    def test_get_folding_ranges_empty_document(self, provider):
        """Test folding ranges for empty document."""
        ranges = provider.get_folding_ranges("")
        assert len(ranges) == 0

    def test_get_folding_ranges_no_sections(self, provider):
        """Test folding ranges without sections."""
        text = """start test
title "No sections"
task dft energy
"""
        ranges = provider.get_folding_ranges(text)
        assert len(ranges) == 0

    def test_get_folding_ranges_unclosed_section(self, provider):
        """Test folding ranges with unclosed section."""
        text = """start test

geometry
  O  0.000  0.000  0.000

task dft
"""
        ranges = provider.get_folding_ranges(text)
        # Unclosed sections generate folding ranges to end of document
        assert len(ranges) == 1
        assert ranges[0].start_line == 2

    def test_get_folding_ranges_for_lines(self, provider):
        """Test folding ranges for specific line range."""
        text = """start test

geometry
  O  0.000  0.000  0.000
end

basis
  * library sto-3g
end
"""
        all_ranges = provider.get_folding_ranges(text)
        assert len(all_ranges) == 2

        # Get ranges for first section only
        filtered = provider.get_folding_ranges_for_lines(text, 0, 5)
        assert len(filtered) == 1
        assert filtered[0].start_line == 2

    def test_provider_creation(self):
        """Test provider creation."""
        provider = FoldingRangeProvider()
        assert provider is not None
        assert provider.server is None

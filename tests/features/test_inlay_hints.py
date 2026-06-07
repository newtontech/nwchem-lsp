"""Tests for inlay hints provider."""

import pytest
from lsprotocol.types import InlayHintKind
from pygls.server import LanguageServer

from nwchem_lsp.features.inlay_hints import InlayHintsProvider


class TestInlayHintsProvider:
    """Test inlay hints provider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        server = LanguageServer("test", "0.1.0")
        return InlayHintsProvider(server)

    def test_provider_exists(self, provider):
        """Test provider can be created."""
        assert provider is not None

    def test_get_inlay_hints_empty(self, provider):
        """Test with empty text."""
        hints = provider.get_inlay_hints("", 0, 0)
        assert hints == []

    def test_get_inlay_hints_geometry(self, provider):
        """Test hints for geometry coordinates."""
        text = """geometry units angstroms
  O 0.000 0.000 0.000
  H 0.000 0.790 0.580
end
"""
        hints = provider.get_inlay_hints(text, 1, 2)
        # Should have coordinate hints
        assert len(hints) >= 1

    def test_get_inlay_hints_task(self, provider):
        """Test hints for task."""
        text = "task dft optimize"
        hints = provider.get_inlay_hints(text, 0, 1)

        assert len(hints) >= 1
        assert "DFT" in hints[0].label

    def test_get_inlay_hints_charge(self, provider):
        """Test hints for charge."""
        text = "charge 0"
        hints = provider.get_inlay_hints(text, 0, 1)

        assert len(hints) >= 1
        assert "neutral" in hints[0].label

    def test_get_inlay_hints_cation(self, provider):
        """Test hints for cation charge."""
        text = "charge 1"
        hints = provider.get_inlay_hints(text, 0, 1)

        assert len(hints) >= 1
        assert "cation" in hints[0].label

    def test_get_inlay_hints_anion(self, provider):
        """Test hints for anion charge."""
        text = "charge -1"
        hints = provider.get_inlay_hints(text, 0, 1)

        assert len(hints) >= 1
        assert "anion" in hints[0].label

    def test_get_inlay_hints_basis_all(self, provider):
        """Test hints for basis library."""
        text = "* library 6-31g*"
        hints = provider.get_inlay_hints(text, 0, 1)

        assert len(hints) >= 1
        assert "all atoms" in hints[0].label

    def test_get_inlay_hints_comment_line(self, provider):
        """Test hints skip comment lines."""
        text = "# This is a comment"
        hints = provider.get_inlay_hints(text, 0, 1)
        assert len(hints) == 0

    def test_get_inlay_hints_convergence(self, provider):
        """Test hints for convergence."""
        text = "thresh 1e-6"
        hints = provider.get_inlay_hints(text, 0, 1)

        assert len(hints) >= 1
        assert "convergence" in hints[0].label

    def test_is_coordinate_line_valid(self, provider):
        """Test coordinate line detection."""
        assert provider._is_coordinate_line(["H", "1.0", "2.0", "3.0"]) is True
        assert provider._is_coordinate_line(["C", "0", "0", "0"]) is True

    def test_is_coordinate_line_invalid(self, provider):
        """Test invalid coordinate lines."""
        assert provider._is_coordinate_line(["H"]) is False
        assert provider._is_coordinate_line(["H", "a", "b", "c"]) is False
        assert provider._is_coordinate_line([]) is False

    def test_describe_charge(self, provider):
        """Test charge descriptions."""
        assert "neutral" in provider._describe_charge(0)
        assert "cation" in provider._describe_charge(1)
        assert "anion" in provider._describe_charge(-1)
        assert "cation" in provider._describe_charge(2)

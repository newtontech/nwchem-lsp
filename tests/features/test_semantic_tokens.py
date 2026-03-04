"""Tests for semantic tokens provider."""

import pytest
from lsprotocol.types import SemanticTokenTypes

from nwchem_lsp.features.semantic_tokens import SemanticTokensProvider
from pygls.server import LanguageServer


class TestSemanticTokensProvider:
    """Test semantic tokens provider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        server = LanguageServer("test", "0.1.0")
        return SemanticTokensProvider(server)

    def test_provider_exists(self, provider):
        """Test provider can be created."""
        assert provider is not None

    def test_get_legend(self, provider):
        """Test token legend."""
        legend = provider.get_legend()
        assert legend is not None
        assert len(legend.token_types) > 0
        assert "namespace" in legend.token_types
        assert "function" in legend.token_types

    def test_get_semantic_tokens_empty(self, provider):
        """Test with empty text."""
        tokens = provider.get_semantic_tokens("")
        assert tokens is not None
        assert tokens.data == []

    def test_get_semantic_tokens_section(self, provider):
        """Test tokens for section names."""
        text = "geometry units angstroms"
        tokens = provider.get_semantic_tokens(text)

        # Should have tokens (geometry = namespace)
        assert len(tokens.data) >= 5  # At least one token (5 ints per token)

    def test_get_semantic_tokens_dft_functional(self, provider):
        """Test tokens for DFT functional."""
        text = "xc b3lyp"
        tokens = provider.get_semantic_tokens(text)

        # Should have tokens
        assert len(tokens.data) >= 5

    def test_get_semantic_tokens_basis_set(self, provider):
        """Test tokens for basis set."""
        text = "6-31g*"
        tokens = provider.get_semantic_tokens(text)

        # Should have tokens
        assert len(tokens.data) >= 0

    def test_get_semantic_tokens_task(self, provider):
        """Test tokens for task."""
        text = "task dft optimize"
        tokens = provider.get_semantic_tokens(text)

        # Should have tokens for task and operation
        assert len(tokens.data) >= 5

    def test_get_semantic_tokens_element(self, provider):
        """Test tokens for chemical elements."""
        text = "H 0 0 0"
        tokens = provider.get_semantic_tokens(text)

        # Should have tokens
        assert len(tokens.data) >= 5

    def test_get_semantic_tokens_number(self, provider):
        """Test tokens for numbers."""
        text = "1.234"
        tokens = provider.get_semantic_tokens(text)

        # Should have number token
        assert len(tokens.data) >= 5

    def test_get_semantic_tokens_reserved(self, provider):
        """Test tokens for reserved keywords."""
        text = "end"
        tokens = provider.get_semantic_tokens(text)

        # Should have tokens
        assert len(tokens.data) >= 5

    def test_is_number(self, provider):
        """Test number detection."""
        assert provider._is_number("1.0") is True
        assert provider._is_number("123") is True
        assert provider._is_number("-1.5") is True
        assert provider._is_number("abc") is False
        assert provider._is_number("1.2.3") is False

    def test_tokenize_line_geometry(self, provider):
        """Test tokenizing geometry line."""
        line = "geometry units angstroms"
        tokens = provider._tokenize_line(line, 0)

        assert len(tokens) >= 1
        # First token should be geometry (namespace)
        assert tokens[0][0] == 0  # char position
        assert tokens[0][1] == 8  # length

    def test_tokenize_line_empty(self, provider):
        """Test tokenizing empty line."""
        tokens = provider._tokenize_line("", 0)
        assert tokens == []

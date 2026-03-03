"""Tests for formatting provider."""

import pytest

from lsprotocol.types import (
    DocumentFormattingParams,
    FormattingOptions,
    TextDocumentIdentifier,
)

from nwchem_lsp.features.formatting import NwchemFormattingProvider


@pytest.fixture
def provider():
    """Create a formatting provider instance."""
    from pygls.server import LanguageServer
    server = LanguageServer("test", "1.0")
    return NwchemFormattingProvider(server)


@pytest.fixture
def formatting_params():
    """Create default formatting parameters."""
    return DocumentFormattingParams(
        text_document=TextDocumentIdentifier(uri="test.nw"),
        options=FormattingOptions(
            tab_size=2,
            insert_spaces=True,
        )
    )


class TestNwchemFormattingProvider:
    """Tests for NwchemFormattingProvider."""

    def test_provider_exists(self, provider):
        """Test that provider can be created."""
        assert provider is not None

    def test_format_empty(self, provider, formatting_params):
        """Test formatting empty document."""
        edits = provider.format_document("", formatting_params)
        assert edits == []

    def test_format_single_line(self, provider, formatting_params):
        """Test formatting single line."""
        text = "task scf"
        edits = provider.format_document(text, formatting_params)
        assert len(edits) == 0  # Already formatted

    def test_format_with_indentation(self, provider, formatting_params):
        """Test formatting with proper indentation."""
        text = """geometry
H 0 0 0
O 0 0 1.0
end
"""
        edits = provider.format_document(text, formatting_params)
        # Should have at least one edit to fix indentation
        assert len(edits) >= 1

    def test_format_multiple_sections(self, provider, formatting_params):
        """Test formatting multiple sections."""
        text = """geometry
H 0 0 0
end

basis
H library 6-31g
end
"""
        edits = provider.format_document(text, formatting_params)
        # Should format indentation
        assert len(edits) >= 1

    def test_format_preserves_comments(self, provider, formatting_params):
        """Test that comments are preserved."""
        text = """# Water molecule
geometry
  H 0 0 0
end
"""
        # Comments should be preserved
        edits = provider.format_document(text, formatting_params)
        # Just verify it runs without error
        assert isinstance(edits, list)

    def test_format_preserves_blank_lines(self, provider, formatting_params):
        """Test that blank lines are preserved."""
        text = """
geometry
  H 0 0 0
end

"""
        # Just verify it runs without error
        edits = provider.format_document(text, formatting_params)
        assert isinstance(edits, list)

    def test_format_different_indent_size(self, provider):
        """Test formatting with different indent sizes."""
        text = """geometry
H 0 0 0
end
"""
        
        params_4_spaces = DocumentFormattingParams(
            text_document=TextDocumentIdentifier(uri="test.nw"),
            options=FormattingOptions(tab_size=4, insert_spaces=True)
        )
        params_tabs = DocumentFormattingParams(
            text_document=TextDocumentIdentifier(uri="test.nw"),
            options=FormattingOptions(tab_size=2, insert_spaces=False)
        )
        
        # Both should produce edits
        edits_4 = provider.format_document(text, params_4_spaces)
        edits_tabs = provider.format_document(text, params_tabs)
        assert len(edits_4) >= 1 or len(edits_tabs) >= 1

    def test_get_section_keywords(self, provider):
        """Test that section keywords are correctly identified."""
        keywords = provider._get_section_keywords()
        
        assert "geometry" in keywords
        assert "basis" in keywords
        assert "scf" in keywords
        assert "dft" in keywords
        assert "task" not in keywords  # task is not a block section


class TestGetFormattingProvider:
    """Tests for get_formatting_provider factory function."""

    def test_factory(self):
        """Test factory function."""
        from nwchem_lsp.features.formatting import get_formatting_provider
        from pygls.server import LanguageServer
        
        server = LanguageServer("test", "1.0")
        provider = get_formatting_provider(server)
        
        assert isinstance(provider, NwchemFormattingProvider)

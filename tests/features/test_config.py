"""Tests for configuration provider."""

import pytest
from pygls.server import LanguageServer

from nwchem_lsp.features.config import ConfigProvider, NwchemConfig, get_config_provider


class TestNwchemConfig:
    """Test NWChem configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = NwchemConfig()
        assert config.indent_size == 2
        assert config.use_tabs is False
        assert config.max_line_length == 80
        assert config.validate_basis_sets is True
        assert config.validate_functionals is True
        assert config.fuzzy_match is True

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "indentSize": 4,
            "useTabs": True,
            "maxLineLength": 120,
            "validateBasisSets": False,
        }
        config = NwchemConfig.from_dict(config_dict)
        assert config.indent_size == 4
        assert config.use_tabs is True
        assert config.max_line_length == 120
        assert config.validate_basis_sets is False
        # Other values should be defaults
        assert config.validate_functionals is True

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = NwchemConfig(indent_size=4, use_tabs=True)
        config_dict = config.to_dict()
        assert config_dict["indentSize"] == 4
        assert config_dict["useTabs"] is True
        assert config_dict["validateBasisSets"] is True


class TestConfigProvider:
    """Test configuration provider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        server = LanguageServer("test", "0.1.0")
        return ConfigProvider(server)

    def test_provider_exists(self, provider):
        """Test provider can be created."""
        assert provider is not None

    def test_get_config(self, provider):
        """Test getting configuration."""
        config = provider.get_config()
        assert isinstance(config, NwchemConfig)
        assert config.indent_size == 2

    def test_update_config(self, provider):
        """Test updating configuration."""
        provider.update_config({"indentSize": 4, "useTabs": True})
        config = provider.get_config()
        assert config.indent_size == 4
        assert config.use_tabs is True

    def test_get_server_capabilities(self, provider):
        """Test server capabilities."""
        caps = provider.get_server_capabilities()
        assert "configurationProvider" in caps
        assert caps["configurationProvider"] is True


class TestGetConfigProvider:
    """Test config provider factory function."""

    def test_factory(self):
        """Test factory creates provider."""
        server = LanguageServer("test", "0.1.0")
        provider = get_config_provider(server)
        assert isinstance(provider, ConfigProvider)

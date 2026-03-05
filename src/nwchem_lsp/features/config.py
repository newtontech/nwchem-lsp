"""LSP configuration management for NWChem.

This module provides configuration options for the NWChem LSP server,
enabling customization via LSP settings.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pygls.server import LanguageServer


@dataclass
class NwchemConfig:
    """Configuration for NWChem LSP server."""

    # Formatting options
    indent_size: int = 2
    use_tabs: bool = False
    max_line_length: int = 80

    # Validation options
    validate_basis_sets: bool = True
    validate_functionals: bool = True
    strict_mode: bool = False

    # Completion options
    case_sensitive: bool = False
    fuzzy_match: bool = True
    max_completions: int = 50

    # Hover options
    show_examples: bool = True
    show_deprecated: bool = True

    # Diagnostic options
    show_warnings: bool = True
    show_info: bool = False
    max_diagnostics: int = 100

    # Inlay hints options
    show_coordinate_units: bool = True
    show_charge_info: bool = True
    show_task_hints: bool = True

    # Semantic tokens options
    enable_semantic_highlighting: bool = True

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "NwchemConfig":
        """Create configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            NwchemConfig instance
        """
        return cls(
            indent_size=config_dict.get("indentSize", 2),
            use_tabs=config_dict.get("useTabs", False),
            max_line_length=config_dict.get("maxLineLength", 80),
            validate_basis_sets=config_dict.get("validateBasisSets", True),
            validate_functionals=config_dict.get("validateFunctionals", True),
            strict_mode=config_dict.get("strictMode", False),
            case_sensitive=config_dict.get("caseSensitive", False),
            fuzzy_match=config_dict.get("fuzzyMatch", True),
            max_completions=config_dict.get("maxCompletions", 50),
            show_examples=config_dict.get("showExamples", True),
            show_deprecated=config_dict.get("showDeprecated", True),
            show_warnings=config_dict.get("showWarnings", True),
            show_info=config_dict.get("showInfo", False),
            max_diagnostics=config_dict.get("maxDiagnostics", 100),
            show_coordinate_units=config_dict.get("showCoordinateUnits", True),
            show_charge_info=config_dict.get("showChargeInfo", True),
            show_task_hints=config_dict.get("showTaskHints", True),
            enable_semantic_highlighting=config_dict.get("enableSemanticHighlighting", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return {
            "indentSize": self.indent_size,
            "useTabs": self.use_tabs,
            "maxLineLength": self.max_line_length,
            "validateBasisSets": self.validate_basis_sets,
            "validateFunctionals": self.validate_functionals,
            "strictMode": self.strict_mode,
            "caseSensitive": self.case_sensitive,
            "fuzzyMatch": self.fuzzy_match,
            "maxCompletions": self.max_completions,
            "showExamples": self.show_examples,
            "showDeprecated": self.show_deprecated,
            "showWarnings": self.show_warnings,
            "showInfo": self.show_info,
            "maxDiagnostics": self.max_diagnostics,
            "showCoordinateUnits": self.show_coordinate_units,
            "showChargeInfo": self.show_charge_info,
            "showTaskHints": self.show_task_hints,
            "enableSemanticHighlighting": self.enable_semantic_highlighting,
        }


class ConfigProvider:
    """Provides configuration management for NWChem LSP."""

    def __init__(self, server: LanguageServer):
        """Initialize the configuration provider.

        Args:
            server: The language server instance
        """
        self.server = server
        self.config = NwchemConfig()

    def update_config(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from dictionary.

        Args:
            config_dict: New configuration values
        """
        self.config = NwchemConfig.from_dict(config_dict)

    def get_config(self) -> NwchemConfig:
        """Get current configuration.

        Returns:
            Current configuration
        """
        return self.config

    def get_server_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities related to configuration.

        Returns:
            Server capabilities dictionary
        """
        return {
            "configurationProvider": True,
        }


def get_config_provider(server: LanguageServer) -> ConfigProvider:
    """Create a configuration provider instance.

    Args:
        server: The language server instance

    Returns:
        Configuration provider instance
    """
    return ConfigProvider(server)

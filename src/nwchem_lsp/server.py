"""nwchem Language Server Protocol implementation."""

from __future__ import annotations

import json
import logging
from typing import Any

from lsprotocol.types import (
    INITIALIZED,
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_FOLDING_RANGE,
    TEXT_DOCUMENT_FORMATTING,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_INLAY_HINT,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_RENAME,
    TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    WORKSPACE_CONFIGURATION,
    WORKSPACE_SYMBOL,
    CodeActionParams,
    CompletionOptions,
    CompletionParams,
    DefinitionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentFormattingParams,
    DocumentSymbolParams,
    FoldingRangeParams,
    HoverParams,
    InitializeParams,
    InlayHintParams,
    ReferenceParams,
    RenameParams,
    SemanticTokensParams,
    ServerCapabilities,
    WorkspaceSymbolParams,
)
from pygls.server import LanguageServer

from .data.keywords import get_all_keyword_names
from .features.code_actions import CodeActionsProvider
from .features.completion import NwchemCompletionProvider
from .features.config import ConfigProvider, get_config_provider
from .features.definition import DefinitionProvider, get_definition_provider
from .features.diagnostic import NwchemDiagnosticProvider
from .features.folding_range import FoldingRangeProvider, get_folding_range_provider
from .features.formatting import NwchemFormattingProvider
from .features.hover import NwchemHoverProvider
from .features.inlay_hints import InlayHintsProvider, get_inlay_hints_provider
from .features.references import ReferencesProvider, get_references_provider
from .features.rename import RenameProvider, get_rename_provider
from .features.semantic_tokens import SemanticTokensProvider, get_semantic_tokens_provider
from .features.symbols import NwchemSymbolProvider
from .features.workspace_symbols import WorkspaceSymbolProvider, get_workspace_symbol_provider

logger = logging.getLogger(__name__)


class NWChemLanguageServer(LanguageServer):
    """NWChem Language Server Protocol implementation."""

    def __init__(self) -> None:
        """Initialize the NWChem language server."""
        super().__init__("nwchem-lsp", "0.5.0")

        # Initialize feature providers
        self.completion_provider = NwchemCompletionProvider(self)
        self.hover_provider = NwchemHoverProvider(self)
        self.diagnostic_provider = NwchemDiagnosticProvider(self)
        self.symbol_provider = NwchemSymbolProvider(self)
        self.formatting_provider = NwchemFormattingProvider(self)
        self.code_actions_provider = CodeActionsProvider()
        self.definition_provider = get_definition_provider()
        self.workspace_symbol_provider = get_workspace_symbol_provider(self)
        self.config_provider = get_config_provider(self)
        self.semantic_tokens_provider = get_semantic_tokens_provider(self)
        self.inlay_hints_provider = get_inlay_hints_provider(self)
        self.folding_range_provider = get_folding_range_provider(self)
        self.references_provider = get_references_provider(self)
        self.rename_provider = get_rename_provider(self)

        # Document cache
        self.documents: dict[str, str] = {}

        # Register handlers
        self._register_handlers()

    def _publish_and_cache(self, uri: str, diagnostics: list) -> None:
        """Publish diagnostics to the client and update the snapshot cache.

        Args:
            uri: Document URI.
            diagnostics: Computed diagnostics.
        """
        self.publish_diagnostics(uri, diagnostics)
        self.diagnostic_provider.update_cache(uri, diagnostics)

    def _register_handlers(self) -> None:
        """Register LSP handlers."""

        @self.feature(TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[" ", "\n"]))
        def completion(params: CompletionParams) -> list[Any]:
            """Handle completion request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Completion requested for unknown document: %s", uri)
                return []

            try:
                text = self.documents[uri]
                return self.completion_provider.get_completions(text, params.position)
            except Exception:
                logger.exception("Error processing completion for %s", uri)
                return []

        @self.feature(TEXT_DOCUMENT_HOVER)
        def hover(params: HoverParams) -> Any:
            """Handle hover request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Hover requested for unknown document: %s", uri)
                return None

            try:
                text = self.documents[uri]
                return self.hover_provider.get_hover(text, params.position)
            except Exception:
                logger.exception("Error processing hover for %s", uri)
                return None

        @self.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
        def document_symbol(params: DocumentSymbolParams) -> list[Any]:
            """Handle document symbol request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Document symbol requested for unknown document: %s", uri)
                return []

            try:
                text = self.documents[uri]
                return self.symbol_provider.get_document_symbols(text)
            except Exception:
                logger.exception("Error processing document symbols for %s", uri)
                return []

        @self.feature(WORKSPACE_SYMBOL)
        def workspace_symbol(params: WorkspaceSymbolParams) -> list[Any]:
            """Handle workspace symbol request."""
            try:
                return self.workspace_symbol_provider.get_workspace_symbols(
                    params.query, self.documents
                )
            except Exception:
                logger.exception("Error processing workspace symbols")
                return []

        @self.feature(TEXT_DOCUMENT_FORMATTING)
        def formatting(params: DocumentFormattingParams) -> list[Any]:
            """Handle formatting request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Formatting requested for unknown document: %s", uri)
                return []

            try:
                text = self.documents[uri]
                return self.formatting_provider.format_document(text, params)
            except Exception:
                logger.exception("Error processing formatting for %s", uri)
                return []

        @self.feature(TEXT_DOCUMENT_DID_OPEN)
        def did_open(params: DidOpenTextDocumentParams) -> None:
            """Handle document open."""
            uri = params.text_document.uri
            text = params.text_document.text
            self.documents[uri] = text

            try:
                # Publish diagnostics
                diagnostics = self.diagnostic_provider.get_diagnostics(text)
                self._publish_and_cache(uri, diagnostics)
            except Exception:
                logger.exception("Error publishing diagnostics on open for %s", uri)

        @self.feature(TEXT_DOCUMENT_DID_CHANGE)
        def did_change(params: DidChangeTextDocumentParams) -> None:
            """Handle document change."""
            uri = params.text_document.uri

            # Get the latest content
            if params.content_changes:
                text = params.content_changes[-1].text
                self.documents[uri] = text

                try:
                    # Publish diagnostics
                    diagnostics = self.diagnostic_provider.get_diagnostics(text)
                    self._publish_and_cache(uri, diagnostics)
                except Exception:
                    logger.exception("Error publishing diagnostics on change for %s", uri)

        @self.feature(TEXT_DOCUMENT_DID_SAVE)
        def did_save(params: DidSaveTextDocumentParams) -> None:
            """Handle document save."""
            uri = params.text_document.uri
            if uri in self.documents:
                text = self.documents[uri]
                try:
                    diagnostics = self.diagnostic_provider.get_diagnostics(text)
                    self._publish_and_cache(uri, diagnostics)
                except Exception:
                    logger.exception("Error publishing diagnostics on save for %s", uri)

        @self.feature(TEXT_DOCUMENT_CODE_ACTION)
        def code_action(params: CodeActionParams) -> list:
            """Handle code action request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Code action requested for unknown document: %s", uri)
                return []

            try:
                text = self.documents[uri]
                diagnostics = params.context.diagnostics if params.context else []
                return self.code_actions_provider.get_code_actions(text, diagnostics)
            except Exception:
                logger.exception("Error processing code actions for %s", uri)
                return []

        @self.feature(TEXT_DOCUMENT_DEFINITION)
        def definition(params: DefinitionParams) -> Any:
            """Handle definition request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Definition requested for unknown document: %s", uri)
                return None

            try:
                text = self.documents[uri]
                return self.definition_provider.get_definition(text, params.position)
            except Exception:
                logger.exception("Error processing definition for %s", uri)
                return None

        @self.feature(TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL)
        def semantic_tokens_full(params: SemanticTokensParams) -> Any:
            """Handle semantic tokens request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Semantic tokens requested for unknown document: %s", uri)
                return None

            try:
                text = self.documents[uri]
                return self.semantic_tokens_provider.get_semantic_tokens(text)
            except Exception:
                logger.exception("Error processing semantic tokens for %s", uri)
                return None

        @self.feature(TEXT_DOCUMENT_FOLDING_RANGE)
        def folding_range(params: FoldingRangeParams) -> list[Any]:
            """Handle folding range request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Folding range requested for unknown document: %s", uri)
                return []

            try:
                text = self.documents[uri]
                return self.folding_range_provider.get_folding_ranges(text)
            except Exception:
                logger.exception("Error processing folding range for %s", uri)
                return []

        @self.feature(TEXT_DOCUMENT_REFERENCES)
        def references(params: ReferenceParams) -> list[Any]:
            """Handle references request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("References requested for unknown document: %s", uri)
                return []

            try:
                text = self.documents[uri]
                return self.references_provider.get_references(
                    text, uri, params.position, params.context.include_declaration
                )
            except Exception:
                logger.exception("Error processing references for %s", uri)
                return []

        @self.feature(TEXT_DOCUMENT_RENAME)
        def rename(params: RenameParams) -> Any:
            """Handle rename request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Rename requested for unknown document: %s", uri)
                return None

            try:
                text = self.documents[uri]
                return self.rename_provider.get_rename_edits(
                    text, uri, params.position, params.new_name
                )
            except Exception:
                logger.exception("Error processing rename for %s", uri)
                return None

        @self.feature(TEXT_DOCUMENT_INLAY_HINT)
        def inlay_hint(params: InlayHintParams) -> list[Any]:
            """Handle inlay hints request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                logger.warning("Inlay hints requested for unknown document: %s", uri)
                return []

            try:
                text = self.documents[uri]
                start_line = params.range.start.line
                end_line = params.range.end.line
                return self.inlay_hints_provider.get_inlay_hints(text, start_line, end_line)
            except Exception:
                logger.exception("Error processing inlay hints for %s", uri)
                return []

        @self.feature(INITIALIZED)
        def initialized(_: Any) -> None:
            """Handle server initialization completion."""
            # Request configuration from client
            pass

        # ------------------------------------------------------------------
        # Custom LSP command: diagnostics snapshot
        # ------------------------------------------------------------------

        @self.command("nwchem.diagnosticsSnapshot")
        def diagnostics_snapshot(arguments: list[Any]) -> str:
            """Return a JSON diagnostics snapshot.

            Accepts an optional URI as the first argument.  When provided,
            returns diagnostics for that single document.  Otherwise returns
            diagnostics for every tracked URI.

            Args:
                arguments: Optional list with a single URI string.

            Returns:
                JSON string of diagnostics.
            """
            uri: str | None = arguments[0] if arguments else None
            return self.diagnostic_provider.snapshot_to_json(uri)


def create_server() -> NWChemLanguageServer:
    """Create and configure the NWChem language server.

    Returns:
        Configured language server instance.
    """
    server = NWChemLanguageServer()
    return server


# Global server instance for backwards compatibility
server = create_server()


def main() -> None:
    """Main entry point for the language server."""
    server.start_io()


if __name__ == "__main__":
    main()

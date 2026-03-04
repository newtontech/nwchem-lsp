"""nwchem Language Server Protocol implementation."""

from __future__ import annotations

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
    TEXT_DOCUMENT_FORMATTING,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_INLAY_HINT,
    TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    TEXT_DOCUMENT_FOLDING_RANGE,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_RENAME,
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
    HoverParams,
    InlayHintParams,
    InitializeParams,
    SemanticTokensParams,
    FoldingRangeParams,
    ReferenceParams,
    RenameParams,
    ServerCapabilities,
    WorkspaceSymbolParams,
)
from pygls.server import LanguageServer

from .data.keywords import get_all_keyword_names
from .features.code_actions import CodeActionsProvider
from .features.completion import NwchemCompletionProvider
from .features.config import ConfigProvider, get_config_provider
from .features.definition import DefinitionProvider, get_definition_provider
from .features.diagnostic import DiagnosticProvider
from .features.formatting import NwchemFormattingProvider
from .features.hover import NwchemHoverProvider
from .features.inlay_hints import InlayHintsProvider, get_inlay_hints_provider
from .features.semantic_tokens import SemanticTokensProvider, get_semantic_tokens_provider
from .features.symbols import NwchemSymbolProvider
from .features.workspace_symbols import WorkspaceSymbolProvider, get_workspace_symbol_provider
from .features.folding_range import FoldingRangeProvider, get_folding_range_provider
from .features.references import ReferencesProvider, get_references_provider
from .features.rename import RenameProvider, get_rename_provider


class NWChemLanguageServer(LanguageServer):
    """NWChem Language Server Protocol implementation."""

    def __init__(self) -> None:
        """Initialize the NWChem language server."""
        super().__init__("nwchem-lsp", "0.5.0")

        # Initialize feature providers
        self.completion_provider = NwchemCompletionProvider(self)
        self.hover_provider = NwchemHoverProvider(self)
        self.diagnostic_provider = DiagnosticProvider(self)
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

    def _register_handlers(self) -> None:
        """Register LSP handlers."""

        @self.feature(TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[" ", "\n"]))
        def completion(params: CompletionParams) -> list[Any]:
            """Handle completion request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return []

            text = self.documents[uri]
            return self.completion_provider.get_completions(text, params.position)

        @self.feature(TEXT_DOCUMENT_HOVER)
        def hover(params: HoverParams) -> Any:
            """Handle hover request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return None

            text = self.documents[uri]
            return self.hover_provider.get_hover(text, params.position)

        @self.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
        def document_symbol(params: DocumentSymbolParams) -> list[Any]:
            """Handle document symbol request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return []

            text = self.documents[uri]
            return self.symbol_provider.get_document_symbols(text)

        @self.feature(WORKSPACE_SYMBOL)
        def workspace_symbol(params: WorkspaceSymbolParams) -> list[Any]:
            """Handle workspace symbol request."""
            return self.workspace_symbol_provider.get_workspace_symbols(
                params.query, self.documents
            )

        @self.feature(TEXT_DOCUMENT_FORMATTING)
        def formatting(params: DocumentFormattingParams) -> list[Any]:
            """Handle formatting request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return []

            text = self.documents[uri]
            return self.formatting_provider.format_document(text, params)

        @self.feature(TEXT_DOCUMENT_DID_OPEN)
        def did_open(params: DidOpenTextDocumentParams) -> None:
            """Handle document open."""
            uri = params.text_document.uri
            text = params.text_document.text
            self.documents[uri] = text

            # Publish diagnostics
            diagnostics = self.diagnostic_provider.get_diagnostics(text)
            self.publish_diagnostics(uri, diagnostics)

        @self.feature(TEXT_DOCUMENT_DID_CHANGE)
        def did_change(params: DidChangeTextDocumentParams) -> None:
            """Handle document change."""
            uri = params.text_document.uri

            # Get the latest content
            if params.content_changes:
                text = params.content_changes[-1].text
                self.documents[uri] = text

                # Publish diagnostics
                diagnostics = self.diagnostic_provider.get_diagnostics(text)
                self.publish_diagnostics(uri, diagnostics)

        @self.feature(TEXT_DOCUMENT_DID_SAVE)
        def did_save(params: DidSaveTextDocumentParams) -> None:
            """Handle document save."""
            uri = params.text_document.uri
            if uri in self.documents:
                text = self.documents[uri]
                diagnostics = self.diagnostic_provider.get_diagnostics(text)
                self.publish_diagnostics(uri, diagnostics)

        @self.feature(TEXT_DOCUMENT_CODE_ACTION)
        def code_action(params: CodeActionParams) -> list:
            """Handle code action request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return []

            text = self.documents[uri]
            diagnostics = params.context.diagnostics if params.context else []
            return self.code_actions_provider.get_code_actions(text, diagnostics)

        @self.feature(TEXT_DOCUMENT_DEFINITION)
        def definition(params: DefinitionParams) -> Any:
            """Handle definition request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return None

            text = self.documents[uri]
            return self.definition_provider.get_definition(text, params.position)

        @self.feature(TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL)
        def semantic_tokens_full(params: SemanticTokensParams) -> Any:
            """Handle semantic tokens request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return None

            text = self.documents[uri]
            return self.semantic_tokens_provider.get_semantic_tokens(text)

        @self.feature(TEXT_DOCUMENT_FOLDING_RANGE)
        def folding_range(params: FoldingRangeParams) -> list[Any]:
            """Handle folding range request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return []

            text = self.documents[uri]
            return self.folding_range_provider.get_folding_ranges(text)

        @self.feature(TEXT_DOCUMENT_REFERENCES)
        def references(params: ReferenceParams) -> list[Any]:
            """Handle references request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return []

            text = self.documents[uri]
            return self.references_provider.get_references(
                text, uri, params.position, params.context.include_declaration
            )

        @self.feature(TEXT_DOCUMENT_RENAME)
        def rename(params: RenameParams) -> Any:
            """Handle rename request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return None

            text = self.documents[uri]
            return self.rename_provider.get_rename_edits(
                text, uri, params.position, params.new_name
            )

        @self.feature(TEXT_DOCUMENT_INLAY_HINT)
        def inlay_hint(params: InlayHintParams) -> list[Any]:
            """Handle inlay hints request."""
            uri = params.text_document.uri
            if uri not in self.documents:
                return []

            text = self.documents[uri]
            start_line = params.range.start.line
            end_line = params.range.end.line
            return self.inlay_hints_provider.get_inlay_hints(text, start_line, end_line)

        @self.feature(INITIALIZED)
        def initialized(_: Any) -> None:
            """Handle server initialization completion."""
            # Request configuration from client
            pass


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

"""nwchem Language Server Protocol implementation."""

from __future__ import annotations

from typing import Any

from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_SAVE,
    CompletionOptions,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    HoverParams,
    InitializeParams,
    ServerCapabilities,
)
from pygls.server import LanguageServer

from .data.keywords import get_all_keyword_names
from .features.completion import NwchemCompletionProvider
from .features.hover import NwchemHoverProvider
from .features.diagnostic import DiagnosticProvider


class NWChemLanguageServer(LanguageServer):
    """NWChem Language Server Protocol implementation."""
    
    def __init__(self) -> None:
        """Initialize the NWChem language server."""
        super().__init__("nwchem-lsp", "0.1.0")
        
        # Initialize feature providers
        self.completion_provider = NwchemCompletionProvider(self)
        self.hover_provider = NwchemHoverProvider(self)
        self.diagnostic_provider = DiagnosticProvider(self)
        
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

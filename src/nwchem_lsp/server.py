"""
nwchem Language Server Protocol implementation
"""

import asyncio
from pygls.server import LanguageServer

server = LanguageServer("nwchem-lsp", "0.1.0")

@server.feature("textDocument/completion")
def completion(params):
    return []

@server.feature("textDocument/hover")
def hover(params):
    return None

@server.feature("textDocument/diagnostic")
def diagnostic(params):
    return []

def main():
    server.start_io()

if __name__ == "__main__":
    main()

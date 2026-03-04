# NWChem LSP Architecture

## Overview

NWChem LSP is a Language Server Protocol implementation for NWChem quantum chemistry software input files.

## Module Structure

### Parser Module
- `NwchemParser`: Main parser class
- `NWchemSection`: Data class representing a section
- `ParseContext`: Context information for cursor position

### Features Module
| Provider | Description |
|----------|-------------|
| Completion | Auto-completion for keywords |
| Hover | Inline documentation |
| Diagnostic | Syntax/error checking |
| Symbols | Document outline |
| Workspace Symbols | Global symbol search |
| Formatting | Code formatting |
| Code Actions | Quick fixes |
| Definition | Go to definition |
| Semantic Tokens | Syntax highlighting |
| Inlay Hints | Inline information |

### Data Module
- Chemical elements (1-118)
- Basis sets
- DFT functionals
- Task operations
- Keywords database

## Testing

- **Total Tests**: 160
- **Coverage**: 100%
- **Test Categories**: Unit, Integration, Parser, Feature

## References

- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [pygls](https://pygls.readthedocs.io/)
- [NWChem](https://nwchemgit.github.io/)

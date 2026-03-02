# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-03

### Added
- Document Symbols support for outline view and navigation
- Code formatting with configurable indentation (spaces or tabs)
- New test suites for symbols and formatting providers
- Enhanced LSP server with documentSymbol and formatting handlers

### Changed
- Updated version from 0.1.0 to 0.2.0
- Improved test coverage from 32 to 50 tests (still 100%)
- Updated documentation with new features

### Fixed
- Fixed parser handling of unclosed sections
- Improved error reporting in diagnostics

## [0.1.0] - 2026-03-02

### Added
- Initial release of NWChem LSP
- Syntax validation for NWChem input files
- Auto-completion for top-level keywords, sections, basis sets, and DFT functionals
- Hover documentation for all keywords
- Diagnostics for unclosed sections and invalid keywords
- Comprehensive keyword database (60+ elements, 50+ basis sets, 30+ DFT functionals)
- Full test coverage (32 tests, 100%)

### Supported Features
- Parsing of .nw and .nwinp files
- Context-aware completions
- Section detection (geometry, basis, scf, dft, mp2, ccsd, etc.)
- Task operation suggestions
- Error detection and reporting
- Editor integrations (VS Code, Neovim, Emacs)

[0.2.0]: https://github.com/newtontech/nwchem-lsp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/newtontech/nwchem-lsp/releases/tag/v0.1.0

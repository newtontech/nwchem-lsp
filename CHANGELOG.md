# Changelog

## [Unreleased]

### Added
- **Go to Definition**: LSP definition support for navigating NWChem input files
  - Jump from 'end' keyword to corresponding section start
  - Support for all section types (geometry, basis, dft, scf, etc.)
- 16 new tests for definition provider feature
- Total test count increased to 118 (100% coverage maintained)

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-03-04

### Added
- **Code Actions (Quick Fixes)**: LSP code actions for common errors
  - Auto-fix unclosed sections by adding 'end' keyword
  - Remove unexpected 'end' keywords
  - Correct common typos with fuzzy matching (gemoetry → geometry, etc.)
  - Add missing 'start' directive
- 20 new tests for code actions feature
- Total test count increased to 102 (100% coverage maintained)

### Changed
- Integrated CodeActionsProvider with LSP server
- Updated documentation to reflect new features

## [0.2.0] - 2026-03-03

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-03-03

### Added
- Comprehensive parser tests (TestParseContext, TestNWchemSection, TestNwchemParser)
- Feature module tests for completion provider (TestNwchemCompletionProvider)
- Feature module tests for hover provider (TestNwchemHoverProvider)
- Feature module tests for diagnostic providers (TestDiagnosticProvider, TestDiagnosticsProvider)
- Test coverage increased from 50 to 82 tests (100% coverage)

### Changed
- Reorganized test structure with parser/ and features/ subdirectories
- Improved test organization and maintainability
- Enhanced edge case testing for parser

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

[0.2.1]: https://github.com/newtontech/nwchem-lsp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/newtontech/nwchem-lsp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/newtontech/nwchem-lsp/releases/tag/v0.1.0

[0.3.0]: https://github.com/newtontech/nwchem-lsp/compare/v0.2.1...v0.3.0

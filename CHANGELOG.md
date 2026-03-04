# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-03-04

### Added
- **Workspace Symbols**: Global symbol search across all open documents
  - Search for sections (geometry, basis, dft, etc.) across workspace
  - Search by title/start directive
  - Full integration with LSP workspace/symbol request
- **Configuration Options**: LSP configuration support
  - Formatting options (indent size, tabs/spaces, max line length)
  - Validation options (basis sets, functionals, strict mode)
  - Completion options (case sensitivity, fuzzy matching)
  - Diagnostic options (warnings, info, max count)
- **Semantic Highlighting**: Token-based syntax highlighting
  - Section names (namespace)
  - Task operations (function)
  - Keywords (variable)
  - Basis sets (type)
  - DFT functionals (property)
  - Chemical elements (class)
  - Numeric values (number)
- **Inlay Hints**: Inline information display
  - Coordinate unit hints (Å)
  - Task operation descriptions
  - Charge state descriptions
  - Convergence threshold hints
- 42 new tests for v0.4.0 features
- Total test count increased to 160 (100% coverage maintained)

### Changed
- Updated version from 0.3.0 to 0.4.0
- Enhanced LSP server with new feature providers

## [0.3.0] - 2026-03-04

### Added
- **Code Actions (Quick Fixes)**: LSP code actions for common errors
  - Auto-fix unclosed sections by adding 'end' keyword
  - Remove unexpected 'end' keywords
  - Correct common typos with fuzzy matching (gemoetry → geometry, etc.)
  - Add missing 'start' directive
- **Go to Definition**: LSP definition support for navigating NWChem input files
  - Jump from 'end' keyword to corresponding section start
- 36 new tests for code actions and definition features
- Total test count increased to 118 (100% coverage maintained)

## [0.2.1] - 2026-03-03

### Added
- Comprehensive parser tests (TestParseContext, TestNWchemSection, TestNwchemParser)
- Feature module tests for completion, hover, and diagnostic providers
- Test coverage increased from 50 to 82 tests (100% coverage)

### Changed
- Reorganized test structure with parser/ and features/ subdirectories

## [0.2.0] - 2026-03-03

### Added
- Document Symbols support for outline view and navigation
- Code formatting with configurable indentation
- Enhanced LSP server with documentSymbol and formatting handlers

### Changed
- Updated version from 0.1.0 to 0.2.0
- Improved test coverage from 32 to 50 tests (still 100%)

## [0.1.0] - 2026-03-02

### Added
- Initial release of NWChem LSP
- Syntax validation for NWChem input files
- Auto-completion for top-level keywords, sections, basis sets, and DFT functionals
- Hover documentation for all keywords
- Diagnostics for unclosed sections and invalid keywords
- Comprehensive keyword database (60+ elements, 50+ basis sets, 30+ DFT functionals)
- Full test coverage (32 tests, 100%)

[0.4.0]: https://github.com/newtontech/nwchem-lsp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/newtontech/nwchem-lsp/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/newtontech/nwchem-lsp/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/newtontech/nwchem-lsp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/newtontech/nwchem-lsp/releases/tag/v0.1.0

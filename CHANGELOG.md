# Change Log

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-02

### Added
- Initial LSP server implementation with pygls
- NWChem input file parser (.nw, .nwinp)
- Context-aware auto-completion provider
  - Top-level keywords
  - Section-specific keywords
  - Basis sets (6-31G*, cc-pVTZ, def2-TZVP, etc.)
  - DFT functionals (B3LYP, PBE, M06-2X, etc.)
  - Task operations (energy, optimize, frequencies, etc.)
- Hover documentation provider
- Diagnostic provider with validation
  - Unclosed section blocks
  - Unknown basis sets and functionals
  - Invalid task operations
  - Missing required blocks
- Comprehensive keyword database
- Example NWChem input files
  - water_dft.nw - DFT geometry optimization
  - ethanol_scf.nw - HF single point energy
  - benzene_mp2.nw - MP2 geometry optimization
- 100% test coverage (32 tests)
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality

### Parser Features
- Section parsing and tracking
- Line context extraction
- Word at cursor detection
- Syntax validation
- Completion context determination

### LSP Features
- textDocument/completion
- textDocument/hover
- textDocument/didOpen
- textDocument/didChange
- textDocument/didSave
- textDocument/publishDiagnostics

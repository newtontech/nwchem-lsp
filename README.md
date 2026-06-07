# nwchem-lsp

[![CI](https://github.com/newtontech/nwchem-lsp/workflows/CI/badge.svg)](https://github.com/newtontech/nwchem-lsp/actions)
[![Coverage](https://codecov.io/gh/newtontech/nwchem-lsp/branch/main/graph/badge.svg)](https://codecov.io/gh/newtontech/nwchem-lsp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Language Server Protocol implementation for NWChem quantum chemistry software.

## Features

### Core LSP Features
- **Syntax Validation**: Real-time diagnostics for NWChem input files
- **Auto-completion**: Context-aware keyword completion
  - Top-level keywords (geometry, basis, scf, dft, etc.)
  - Section-specific keywords
  - Basis sets and DFT functionals
  - Task operations and theories
- **Hover Documentation**: Inline help for all keywords
- **Document Symbols**: Outline view and navigation
- **Code Formatting**: Automatic code formatting
- **Go to Definition**: Navigate from 'end' to section start

### v0.5.0 Features
- **Folding Ranges**: Code folding for sections
- **Find References**: Navigate to section occurrences
- **Rename Refactoring**: Rename sections safely

### v0.4.0 Features
- **Workspace Symbols**: Global symbol search across all open documents
- **Configuration Options**: Customizable LSP settings
- **Semantic Highlighting**: Token-based syntax coloring
- **Inlay Hints**: Inline information display (units, charge states, etc.)

### Code Actions (Quick Fixes)
- Add missing 'end' keywords for unclosed sections
- Remove unexpected 'end' keywords
- Correct common typos (gemoetry → geometry, etc.)
- Add missing 'start' directive

### Error Detection
- Unclosed section blocks
- Unknown basis sets and functionals
- Invalid task operations
- Missing required blocks

## Installation

```bash
pip install nwchem-lsp
```

## Usage

### Command Line
```bash
nwchem-lsp
```

### Editor Configuration

#### VS Code
Add to your `settings.json`:
```json
{
  "languageserver": {
    "nwchem": {
      "command": "nwchem-lsp",
      "filetypes": ["nw", "nwinp"],
      "rootPatterns": ["*.nw", "*.nwinp"]
    }
  }
}
```

#### Neovim (nvim-lspconfig)
```lua
local lspconfig = require('lspconfig')
lspconfig.nwchem.setup {
  cmd = {"nwchem-lsp"},
  filetypes = {"nw", "nwinp"},
}
```

#### Emacs (lsp-mode)
```elisp
(lsp-register-client
 (make-lsp-client :new-connection (lsp-stdio-connection "nwchem-lsp")
                  :major-modes '(nwchem-mode)
                  :server-id 'nwchem-lsp))
```

## Supported File Extensions

- `.nw` - NWChem input files
- `.nwinp` - NWChem input files (alternative extension)

## Example NWChem Input

```nwchem
start water

title "Water molecule DFT optimization"

geometry units angstroms
  O  0.000  0.000  0.000
  H  0.000  0.790  0.580
  H  0.000 -0.790  0.580
end

basis spherical
  * library 6-31G*
end

dft
  xc b3lyp
  grid fine
end

task dft optimize
```

See the `examples/` directory for more sample input files.

## Changelog

### v0.5.0 (2026-03-05)
- ✨ Added Folding Ranges support
- ✨ Added Find References support
- ✨ Added Rename Refactoring support
- 🧪 Increased test coverage to 186 tests (100%)


### v0.4.0 (2026-03-04)
- ✨ Added Workspace Symbols support
- ✨ Added Configuration Options (LSP settings)
- ✨ Added Semantic Highlighting
- ✨ Added Inlay Hints
- 🧪 Increased test coverage to 160 tests (100%)

### v0.3.0 (2026-03-04)
- ✨ Added Code Actions (Quick Fixes) support
- ✨ Added Go to Definition support
- 🧪 Increased test coverage to 118 tests (100%)

### v0.2.0 (2026-03-03)
- ✨ Added Document Symbols support
- ✨ Added code formatting
- 🧪 Increased test coverage to 82 tests (100%)

## Development

### Setup
```bash
git clone https://github.com/newtontech/nwchem-lsp.git
cd nwchem-lsp
pip install -e ".[dev]"
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_keywords.py -v
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

## Architecture

```
src/nwchem_lsp/
├── __init__.py
├── server.py           # LSP server implementation
├── parser/
│   └── nwchem_parser.py # NWChem input file parser
├── features/
│   ├── completion.py   # Auto-completion provider
│   ├── hover.py        # Hover documentation provider
│   ├── diagnostic.py   # Diagnostics provider
│   ├── symbols.py      # Document symbols provider
│   ├── formatting.py   # Code formatting provider
│   ├── code_actions.py # Code actions/quick fixes
│   ├── definition.py   # Go to definition provider
│   ├── workspace_symbols.py  # Workspace symbols (v0.4.0)
│   ├── semantic_tokens.py    # Semantic highlighting (v0.4.0)
│   ├── inlay_hints.py        # Inlay hints (v0.4.0)
│   └── config.py             # Configuration management (v0.4.0)
└── data/
    └── keywords.py     # Keyword database
```

## Supported Keywords

### Top-Level Sections
- `geometry` - Molecular geometry definition
- `basis` - Basis set specification
- `scf` - Hartree-Fock calculations
- `dft` - Density functional theory
- `mp2` - MP2 perturbation theory
- `ccsd` - Coupled cluster methods
- `ecp` - Effective core potentials

### Task Operations
- `energy` - Single point energy
- `optimize` - Geometry optimization
- `frequencies` - Vibrational analysis
- `hessian` - Hessian calculation
- `dynamics` - Molecular dynamics

### Supported Basis Sets
STO-3G, 3-21G, 6-31G*, 6-311G**, cc-pVDZ, cc-pVTZ, aug-cc-pVTZ, def2-SVP, def2-TZVP, LANL2DZ, and more.

### Supported DFT Functionals
B3LYP, PBE, PBE0, M06-2X, wB97X-D, CAM-B3LYP, SCAN, and more.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [pygls](https://github.com/openlawlibrary/pygls) - Python LSP framework
- [NWChem](https://nwchem-sw.github.io/) - NWChem quantum chemistry software

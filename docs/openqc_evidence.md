# OpenQC Evidence Report

Language detection, CLI availability, and compatibility analysis for `nwchem-lsp`.

## 1. Language Detection

| Indicator | Value |
|-----------|-------|
| Primary language | Python |
| LSP framework | pygls (Python Generic Language Server) |
| Server type | Language Server Protocol (LSP) |
| NWChem file extension | `.nw` |
| Language ID (LSP) | `nwchem` |

### Detection Logic

The NWChem LSP registers itself for `.nw` files via the `textDocument/didOpen` handler. The server uses `nwchem` as the language identifier in LSP diagnostics and hover responses.

## 2. CLI Availability

| Command | Status | Notes |
|---------|--------|-------|
| `nwchem-lsp` | Not installed as CLI | Package provides LSP server via `python -m nwchem_lsp.server` |
| `python -m nwchem_lsp.server` | Available | Main entry point for the LSP server |
| `nwchem` (NWChem binary) | Not bundled | Requires separate NWChem installation |

### Installation

```bash
pip install -e ".[dev]"
```

### Running the Server

```bash
python -m nwchem_lsp.server
```

The server communicates over stdin/stdout using the LSP JSON-RPC protocol.

## 3. Compatibility Matrix

### NWChem Versions

| Version | Support Status | Evidence |
|---------|---------------|----------|
| NWChem 7.0+ | Primary target | Rule registry based on NWChem 7.0 documentation |
| NWChem 6.x | Partial | Most keywords remain valid; some newer blocks may not parse |
| NWChem 5.x | Legacy | Parser may produce false positives for deprecated syntax |

### LSP Protocol Versions

| LSP Version | Status |
|-------------|--------|
| 3.17 | Fully supported |
| 3.16 | Compatible |
| 3.15 | Compatible |

### Editor Compatibility

| Editor | Integration Method | Status |
|--------|-------------------|--------|
| VS Code | LSP client extension | Primary target |
| Neovim | nvim-lspconfig | Compatible |
| Emacs | eglot/lsp-mode | Compatible |
| Vim | coc.nvim | Compatible |

## 4. Diagnostic Coverage

### Rule Registry (NW000–NW009)

| Rule ID | Description | Severity | Blocking |
|---------|-------------|----------|----------|
| NW001 | Unknown theory/block name | error | Yes |
| NW002 | Missing required block (geometry) | error | Yes |
| NW003 | Unknown basis set name | warning | No |
| NW004 | Unknown operation | warning | No |
| NW005 | Unknown functional | warning | No |
| NW006 | Unusual maxiter value | warning | No |
| NW007 | Invalid maxiter syntax | error | Yes |
| NW008 | Unexpected end of input | error | Yes |
| NW009 | Unclosed section | error | Yes |
| NW000 | Catch-all / generic error | warning | No |

### Fix Preview Coverage

| Rule ID | Fix Action | Alternatives |
|---------|-----------|--------------|
| NW001 | replace | scf, dft, mp2, ccsd, tddft |
| NW002 | insert | (geometry block template) |
| NW003 | replace | sto-3g, 6-31g*, 6-311g**, cc-pvdz |
| NW004 | replace | energy, gradient, optimize, frequency |
| NW005 | replace | b3lyp, pbe, HF, lda |
| NW006 | replace | (numeric suggestion) |
| NW007 | replace | (numeric suggestion) |
| NW008 | None | (no fix available) |
| NW009 | None | (no fix available) |

## 5. Source Provenance Traceability

Each diagnostic rule is linked to official NWChem documentation:

- **NW001**: [Task keyword](https://nwchemgit.github.io/Task.html)
- **NW002**: [Geometry module](https://nwchemgit.github.io/Geometry.html)
- **NW003**: [Basis sets](https://nwchemgit.github.io/Basis.html)
- **NW004**: [Task operations](https://nwchemgit.github.io/Task.html)
- **NW005**: [DFT functionals](https://nwchemgit.github.io/DFT.html)
- **NW006–NW007**: [SCF module](https://nwchemgit.github.io/SCF.html)
- **NW008–NW009**: Parser-level analysis

## 6. Test Coverage

| Component | Coverage |
|-----------|----------|
| `src/nwchem_lsp/features/diagnostic.py` | 100% |
| All fixture tests | Passing |
| Closed-loop validation | All 7 fixtures pass |

## 7. Limitations

1. **NWChem binary not bundled**: The LSP does not invoke NWChem itself; all analysis is static.
2. **Grammar coverage**: The parser covers the most common NWChem blocks; niche or deprecated syntax may produce false positives.
3. **Semantic analysis**: The LSP performs syntactic analysis only; it does not validate chemical correctness (e.g., basis set suitability for a given system).
4. **Cross-block validation**: The LSP does not validate consistency between blocks (e.g., ensuring a DFT functional is compatible with the requested task).

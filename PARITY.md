# Parser Parity

## Parser Status

| Parser | Location | Status |
|--------|----------|--------|
| **Python** (authoritative) | `src/nwchem_lsp/parser/nwchem_parser.py` | Active, tested, distributed |
| **TypeScript** (orphaned) | `src/parsers/nw.ts` | Deprecated, reference only |

The Python parser is the sole authoritative implementation used by the LSP
server. The TypeScript parser was an early prototype and is no longer built,
tested, or included in any distribution pipeline.

## Feature Coverage Matrix

| Feature | Python | TypeScript | Notes |
|---------|--------|------------|-------|
| Section keyword set | Yes | Yes | Identical sets |
| Top-level keyword set | Yes | Yes | Identical sets |
| Section parsing (`_parse_sections`) | Yes | Yes | Same algorithm |
| `get_section_at_line` | Yes | Yes | Same logic |
| `get_context` | Yes | Yes | Same return shape |
| `get_completion_context` | Yes | Yes | Same completion types |
| `is_valid_syntax` | Yes | Yes | Same error messages |
| `get_all_sections` | Yes | Yes | |
| `get_section_content` | Yes | Yes | Case-sensitive lookup in Python |
| `parse()` (blocks) | Yes | No | Python-only: returns section + task blocks |
| `validate()` (dict output) | Yes | No | Python-only: dict-formatted errors |
| `parse_task_directives` | Yes | Yes | Both return structured data with default `'energy'` operation |
| `parse_geometry_block` | Yes | Yes | Both return atoms, units, tags |
| `parse_basis_blocks` | Yes | Yes | Both return library flag, basis set, elements |
| `parse_scf_block` | Yes | Yes | Both return maxiter, thresh, tol2e, direct, vectors |
| `get_line_keywords` | Yes | Yes | Standalone utility function |
| `parse_nwchem_source` | Yes | Yes | Convenience factory function |
| Word extraction at cursor | Yes | Yes | Minor: TS includes `_` in regex, Python uses `isalnum()` |

## Known Behavioral Differences

### 1. Word extraction character set

- **TypeScript**: Uses `/[a-zA-Z0-9_]/` regex, which includes underscores.
- **Python**: Uses `str.isalnum()`, which does not include underscores.

This is unlikely to matter in practice since NWChem identifiers rarely contain
underscores, but it is a known minor difference.

### 2. Section content lookup case sensitivity

- **TypeScript**: `getSectionContent` lowercases the lookup: `section.name.toLowerCase()`.
- **Python**: `get_section_content` uses the section name as-is from the `sections` dict.

Since all section names are stored in lowercase internally by both parsers, this
difference is not observable in practice.

### 3. TypeScript-specific data structures

The TypeScript parser defines explicit interfaces (`GeometryBlock`, `BasisBlock`,
`SCFBlock`, `TaskDirective`, `AtomCoordinate`). The Python parser now has matching
dataclasses (`GeometryBlock`, `BasisBlock`, `SCFBlock`, `TaskDirective`,
`AtomCoordinate`) for full parity.

### 4. `parse_basis_blocks` vs `parseBasisBlock`

- **TypeScript**: `parseBasisBlock()` returns an array of all basis blocks.
- **Python**: `parse_basis_blocks()` (note plural) returns the same, matching the
  TypeScript behavior. Named differently to avoid confusion with the singular
  `parse_geometry_block`/`parse_scf_block` which return the first block only.

## Test Coverage

Parity tests live in `tests/test_parser_parity.py` and mirror the TypeScript test
suite in `tests/parsers/nw.test.ts`. Each test class corresponds to a `describe`
block in the TypeScript tests:

| Test Class | TS `describe` Block | Tests |
|------------|---------------------|-------|
| `TestTaskDirectiveParsing` | Task Directive Parsing | 5 |
| `TestStructuredTaskDirectives` | Task Directive Parsing (structured) | 5 |
| `TestSectionParsing` | Section Management | 7 |
| `TestGeometryBlockParsing` | Geometry Block Parsing | 4 |
| `TestBasisBlockParsing` | Basis Block Parsing | 3 |
| `TestSCFBlockParsing` | SCF Block Parsing | 7 |
| `TestSyntaxValidation` | Syntax Validation | 3 |
| `TestContextParsing` | Context Parsing | 3 |
| `TestEdgeCases` | Basic Parsing + Full Integration | 4 |

Total parity tests: 41

## Maintenance Notes

- The TypeScript parser is **deprecated** and should not receive new features.
- When adding features to the Python parser, update `tests/test_parser_parity.py`
  to maintain coverage alignment.
- The parity tests validate that the Python parser handles at least everything
  the TypeScript parser handles, not the other way around.

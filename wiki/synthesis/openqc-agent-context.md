# OpenQC Agent Context

OpenQC consumes `nwchem-lsp-tool` and `lsp-capabilities.json` to assemble
diagnostics, hover, completion, symbols, examples, next-token guidance, and
repair-plan hints for `nwchem` documents.

## Closed-loop repair previews (`nwchem-lsp-tool fix`)

`nwchem-lsp-tool fix <path> --format json` returns one action per
diagnostic. Each action carries the OpenQC contract fields so agents and
`lsp:check-family` can decide which preview to apply without re-running the
LSP:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Human-readable summary of the repair (or refusal). |
| `kind` | string | Always `"quickfix"`. |
| `diagnostic_code` | string | Stable rule ID (`NW1001`-`NW2012`, `NWCHEM-E044`, etc.). |
| `diagnostic_range` | object | Absolute LSP range (0-based line/character) of the diagnostic. |
| `confidence` | number | Inherited from the diagnostic. |
| `blocking` | boolean | Inherited from the diagnostic. |
| `safe_to_auto_apply` | boolean | `true` for deterministic repairs; `false` for refusals. |
| `edit` | object or `null` | `{"edits": [{"range": ..., "new_text": ...}]}` when safe; `null` when refused. |
| `refusal_reason` | string or `null` | Stable rule-scoped reason when `safe_to_auto_apply === false`; `null` when safe. |

### Safe deterministic repairs

The LSP-side `CodeActionsProvider` produces deterministic text edits for
these rule codes (issue #99):

| Rule | Repair | Edit shape |
|------|--------|------------|
| `NW1001` | Insert `end` after the unclosed section | insertion at end of section |
| `NW1002` | Remove the stray `end` line | deletion of one line |
| `NW2001` | Typo correction (e.g. `gemoetry` -> `geometry`) | in-place token replacement |
| `NW2002` | Replace invalid enum value with closest match | in-place token replacement |
| `NW2004` | Insert a stub for the missing required section | insertion at end of file |
| `NW2005` | Correct unknown task theory to closest valid theory | in-place token replacement |
| `NW2006` | Correct unknown task operation to closest valid operation | in-place token replacement |
| `NW2007` | Suggest closest known basis set | in-place token replacement |
| `NW2008` | Suggest closest known DFT functional | in-place token replacement |
| `NW2009` | Correct unknown top-level directive typo | in-place token replacement |
| `NW2010` | Remove the duplicate section block | deletion of one block |

### Explicit refusals with explanation

Diagnostics whose rule code is not in the table above (or whose handler
cannot produce a deterministic edit) are returned with `safe_to_auto_apply=false`,
`edit=null`, and a rule-scoped `refusal_reason` so agents know exactly why
the LSP refuses to auto-rewrite the region:

| Rule | Refusal reason (paraphrased) |
|------|------------------------------|
| `NWCHEM-E044` | Runtime/output finding; the LSP cannot rewrite the input deterministically. |
| `NW2003` | Type mismatch; the LSP cannot pick a replacement value without scientific intent. |
| `NW2011` | Keyword invalid in section; the LSP cannot decide between move and delete. |
| `NW2012` | Malformed coordinates; the LSP cannot invent numeric coordinates. |
| `NW1003` | Empty section block; the LSP cannot decide between delete and leave as placeholder. |
| (other) | Generic refusal: this diagnostic requires user intent. |

Verified by `tests/test_closed_loop_fix_previews.py`.

# Agent Verification Loop for NWChem LSP

## Overview

This document describes the recommended verification loop for coding agents
(Claude Code, OpenCode, Codex) working with NWChem input files using the
NWChem LSP server.

## Quick Start

1. **Start the LSP server**: The server communicates via stdio.
2. **Send a `textDocument/didOpen` notification** with the source content.
3. **Request diagnostics** to get real-time feedback.
4. **Make edits** via `textDocument/didChange`.
5. **Re-request diagnostics** to verify changes.
6. **Use the agent API** for structured machine-readable output.

## Agent API Endpoints

The NWChem LSP provides custom commands for agent consumption:

- `NWChem.diagnosticsSnapshot` — Returns JSON snapshot of all diagnostics.
- Agent API provider — Returns structured code intelligence.

## Verification Workflow

```
1. Agent reads source file
2. Agent calls diagnostics API
3. If errors found:
   a. Agent analyzes error messages
   b. Agent applies fixes
   c. Agent re-requests diagnostics
4. Repeat until clean
```

## Example

```python
# After editing, request diagnostics
diags = server.get_diagnostics(source)
for d in diags:
    print(f"Line {d.range.start.line}: {d.message}")

# Use agent API for structured output
snapshot = agent_api.get_snapshot(source)
print(f"Found {len(snapshot.diagnostics)} issues")
```

## Golden Regression Testing

Use the regression harness to verify stable behavior:

```python
harness = RegressionHarness()
harness.add_fixture(GoldenFixture(
    name="basic_scf",
    input_source="title test\ntask scf\nend\n",
    expected_diagnostics=[],
))
results = harness.run_all()
assert all(r.passed for r in results)
```

## Test Runner Integration

When a solver binary is available, the test runner provides additional validation:

```python
config = TestRunnerConfig(executable="NWChem", enabled=True)
runner = TestRunnerProvider(config)
diags = runner.run_with_captured_output(captured_output)
```

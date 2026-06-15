"""Optional test-runner / dry-run bridge for NWChem.

Provides an opt-in command that runs NWChem validation or dry-run checks
when the binary is configured, and maps solver output back into LSP
diagnostics.

The feature is disabled by default (no executable configured). CI uses
captured output fixtures so tests never depend on a live NWChem binary.

Wiki
----
- `wiki/entities/LSP_Server.md`_ — LSP Server features
- `wiki/concepts/diagnostic-engine-v1.md`_ — Diagnostic engine v1 contract
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------


@dataclass
class TestRunnerConfig:
    """Configuration for the NWChem test runner."""

    executable: str = ""
    timeout: float = 30.0
    enabled: bool = False

    def validate(self) -> List[str]:
        """Return a list of configuration errors."""
        errors: List[str] = []
        if self.enabled and not self.executable:
            errors.append("NWChem executable path is not configured")
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        return errors


@dataclass
class SolverOutput:
    """Parsed output from a solver dry-run."""

    success: bool = True
    raw_output: str = ""
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)


# ------------------------------------------------------------------
# Output parser
# ------------------------------------------------------------------

# NWChem error patterns
_ERROR_PATTERNS: List[tuple] = [
    (
        re.compile(r"^\s*(\d+)\s*:\s*(?:error|Error|ERROR)\s*:\s*(.+)$", re.MULTILINE),
        "error",
    ),
    (
        re.compile(r"^\s*(\d+)\s*:\s*(?:warning|Warning|WARN)\s*:\s*(.+)$", re.MULTILINE),
        "warning",
    ),
    (
        re.compile(r"Runtime error:\s*(.+?)(?:\n|$)", re.MULTILINE),
        "error",
    ),
    (
        re.compile(r"input error:\s*(.+?)(?:\n|$)", re.MULTILINE),
        "error",
    ),
]

# Pattern to extract line numbers from NWChem errors
_LINE_NUM_RE = re.compile(r"line\s+(\d+)", re.IGNORECASE)


def parse_solver_output(raw: str) -> SolverOutput:
    """Parse NWChem output into structured diagnostics."""
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    for pattern, severity in _ERROR_PATTERNS:
        for match in pattern.finditer(raw):
            message = match.group(match.lastindex).strip()
            line_num = 0

            # The first group might be a line number (e.g., "  5: error: msg")
            if match.lastindex >= 2:
                try:
                    line_num = int(match.group(1).strip()) - 1  # 0-indexed
                except ValueError:
                    pass

            # Also try to extract line number from the message itself
            line_match = _LINE_NUM_RE.search(message)
            if line_match and line_num == 0:
                line_num = int(line_match.group(1)) - 1  # 0-indexed

            entry = {
                "message": message,
                "line": line_num,
                "source": "nwchem-test-runner",
            }
            if severity == "error":
                errors.append(entry)
            else:
                warnings.append(entry)

    return SolverOutput(
        success=len(errors) == 0,
        raw_output=raw,
        errors=errors,
        warnings=warnings,
    )


def solver_output_to_diagnostics(output: SolverOutput) -> List[Diagnostic]:
    """Convert parsed solver output to LSP diagnostics."""
    diagnostics: List[Diagnostic] = []

    for err in output.errors:
        diagnostics.append(
            Diagnostic(
                range=Range(
                    start=Position(line=err["line"], character=0),
                    end=Position(line=err["line"], character=999),
                ),
                message=err["message"],
                severity=DiagnosticSeverity.Error,
                source="nwchem-test-runner",
                code="NW9001",
            )
        )

    for warn in output.warnings:
        diagnostics.append(
            Diagnostic(
                range=Range(
                    start=Position(line=warn["line"], character=0),
                    end=Position(line=warn["line"], character=999),
                ),
                message=warn["message"],
                severity=DiagnosticSeverity.Warning,
                source="nwchem-test-runner",
                code="NW9002",
            )
        )

    return diagnostics


# ------------------------------------------------------------------
# Test Runner Provider
# ------------------------------------------------------------------


class TestRunnerProvider:
    """Provides test-runner / dry-run functionality for NWChem inputs."""

    def __init__(self, config: Optional[TestRunnerConfig] = None) -> None:
        self._config = config or TestRunnerConfig()

    @property
    def config(self) -> TestRunnerConfig:
        return self._config

    @config.setter
    def config(self, value: TestRunnerConfig) -> None:
        self._config = value

    def validate_config(self) -> List[str]:
        """Validate the current configuration."""
        return self._config.validate()

    def run_validation(self, source: str) -> List[Diagnostic]:
        """Run NWChem validation on the given source text.

        Returns a list of LSP diagnostics. When the executable is not
        configured or not found, returns a single information diagnostic.
        """
        if not self._config.enabled:
            return [
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=0, character=0),
                    ),
                    message="NWChem test runner is not enabled. "
                    "Configure the executable path to enable.",
                    severity=DiagnosticSeverity.Information,
                    source="nwchem-test-runner",
                    code="NW9000",
                )
            ]

        if not self._config.executable:
            return [
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=0, character=0),
                    ),
                    message="NWChem executable path is not configured.",
                    severity=DiagnosticSeverity.Warning,
                    source="nwchem-test-runner",
                    code="NW9000",
                )
            ]

        # Check if executable exists
        import shutil

        if not shutil.which(self._config.executable):
            return [
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=0, character=0),
                    ),
                    message=f"NWChem executable not found: {self._config.executable}",
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-test-runner",
                    code="NW9000",
                )
            ]

        # Write to temp file and run
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".nw", delete=False) as f:
                f.write(source)
                temp_path = f.name

            result = subprocess.run(
                [self._config.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=self._config.timeout,
            )

            raw_output = result.stdout + "\n" + result.stderr
            output = parse_solver_output(raw_output)
            return solver_output_to_diagnostics(output)

        except subprocess.TimeoutExpired:
            return [
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=0, character=0),
                    ),
                    message=f"NWChem validation timed out after {self._config.timeout}s.",
                    severity=DiagnosticSeverity.Warning,
                    source="nwchem-test-runner",
                    code="NW9003",
                )
            ]
        except FileNotFoundError:
            return [
                Diagnostic(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=0, character=0),
                    ),
                    message=f"NWChem executable not found: {self._config.executable}",
                    severity=DiagnosticSeverity.Error,
                    source="nwchem-test-runner",
                    code="NW9000",
                )
            ]
        finally:
            try:
                Path(temp_path).unlink()
            except (NameError, FileNotFoundError):
                pass

    def run_with_captured_output(self, captured_output: str) -> List[Diagnostic]:
        """Process pre-captured solver output (for testing/CI).

        This method does not require a live NWChem binary.
        """
        output = parse_solver_output(captured_output)
        return solver_output_to_diagnostics(output)

    def snapshot_config(self) -> str:
        """Return current configuration as JSON for agent consumption."""
        return json.dumps(
            {
                "enabled": self._config.enabled,
                "executable": self._config.executable or "(not configured)",
                "timeout": self._config.timeout,
            },
            indent=2,
        )

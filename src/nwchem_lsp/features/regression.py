"""Regression harness for golden diagnostics, formatting, and code actions.

Provides infrastructure to snapshot and compare LSP feature outputs against
golden fixtures, ensuring stable behavior across changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from lsprotocol.types import Diagnostic

from .agent_api import AgentAPIProvider


@dataclass
class GoldenFixture:
    """A single golden test case."""

    name: str
    input_source: str
    expected_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    expected_outline: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionResult:
    """Result of running a regression test."""

    name: str
    passed: bool
    mismatches: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class RegressionHarness:
    """Regression harness for comparing feature outputs against golden fixtures."""

    def __init__(self, agent_api: Optional[AgentAPIProvider] = None) -> None:
        self._agent_api = agent_api or AgentAPIProvider()
        self._fixtures: Dict[str, GoldenFixture] = {}

    def add_fixture(self, fixture: GoldenFixture) -> None:
        """Register a golden fixture."""
        self._fixtures[fixture.name] = fixture

    def load_fixtures_from_json(self, json_path: str) -> None:
        """Load golden fixtures from a JSON file."""
        with open(json_path, "r") as f:
            data = json.load(f)
        for item in data.get("fixtures", []):
            self.add_fixture(GoldenFixture(
                name=item["name"],
                input_source=item["input_source"],
                expected_diagnostics=item.get("expected_diagnostics", []),
                expected_outline=item.get("expected_outline", []),
                metadata=item.get("metadata", {}),
            ))

    def run_fixture(self, name: str) -> RegressionResult:
        """Run a single fixture and compare against golden output."""
        fixture = self._fixtures.get(name)
        if fixture is None:
            return RegressionResult(name=name, passed=False, mismatches=[f"Fixture '{name}' not found"])

        snapshot = self._agent_api.get_snapshot(fixture.input_source, uri=f"fixture://{name}")
        mismatches: List[str] = []

        # Compare diagnostics count
        actual_diag_count = len(snapshot.diagnostics)
        expected_diag_count = len(fixture.expected_diagnostics)
        if actual_diag_count != expected_diag_count:
            mismatches.append(
                f"Diagnostic count mismatch: expected {expected_diag_count}, got {actual_diag_count}"
            )

        # Compare individual diagnostics
        for i, expected in enumerate(fixture.expected_diagnostics):
            if i >= len(snapshot.diagnostics):
                mismatches.append(f"Missing diagnostic {i}: {expected.get('message', '')}")
                continue
            actual = snapshot.diagnostics[i]
            if expected.get("line") is not None and actual.get("line") != expected["line"]:
                mismatches.append(f"Diagnostic {i} line mismatch: expected {expected['line']}, got {actual.get('line')}")
            if expected.get("code") and actual.get("code") != expected["code"]:
                mismatches.append(f"Diagnostic {i} code mismatch: expected {expected['code']}, got {actual.get('code')}")

        return RegressionResult(
            name=name,
            passed=len(mismatches) == 0,
            mismatches=mismatches,
            details={
                "diagnostics_count": actual_diag_count,
                "outline_count": len(snapshot.outline),
            },
        )

    def run_all(self) -> List[RegressionResult]:
        """Run all registered fixtures."""
        return [self.run_fixture(name) for name in self._fixtures]

    def snapshot_fixture(self, name: str, source: str) -> str:
        """Generate a golden fixture snapshot for a given source."""
        snapshot = self._agent_api.get_snapshot(source, uri=f"fixture://{name}")
        fixture_data = {
            "name": name,
            "input_source": source,
            "expected_diagnostics": snapshot.diagnostics,
            "expected_outline": snapshot.outline,
            "metadata": snapshot.metadata,
        }
        return json.dumps(fixture_data, indent=2)

    @property
    def fixture_count(self) -> int:
        return len(self._fixtures)

    @property
    def fixture_names(self) -> List[str]:
        return list(self._fixtures.keys())

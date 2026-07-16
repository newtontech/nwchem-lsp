from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import nwchem_lsp

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "0.5.0"


def _project_version() -> str:
    match = re.search(
        r'^version = "([^"]+)"$',
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert match is not None
    return match.group(1)


def test_release_version_and_manifest_are_consistent() -> None:
    manifest = json.loads((ROOT / "lsp-capabilities.json").read_text(encoding="utf-8"))

    assert _project_version() == RELEASE_VERSION
    assert nwchem_lsp.__version__ == RELEASE_VERSION
    assert manifest["releaseVersion"] == RELEASE_VERSION
    assert manifest["releaseTag"] == f"v{RELEASE_VERSION}"
    assert manifest["repository"] == "newtontech/nwchem-lsp"
    assert "logs" in manifest["agentCli"]["operations"]


def test_release_workflow_uses_one_artifact_and_scoped_oidc() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert re.search(r"push:\s*\n\s+tags:\s*\[?\"v\*\"\]?", workflow)
    assert "workflow_dispatch:" not in workflow
    assert "cancel-in-progress: false" in workflow
    assert "environment: pypi" in workflow
    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b" in workflow
    assert workflow.count("actions/checkout@v4") >= 2
    assert "GH_REPO: ${{ github.repository }}" in workflow
    assert "release-distributions" in workflow
    assert "gh release create" in workflow
    assert "scripts/verify_release.py" in workflow
    assert "scripts/smoke_wheel.sh" in workflow


def test_release_docs_and_smoke_cover_acceptance_surface() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts" / "smoke_wheel.sh").read_text(encoding="utf-8")

    assert f"Current release: `{RELEASE_VERSION}`" in readme
    assert "Trusted Publishing" in readme
    assert f"## [{RELEASE_VERSION}] - 2026-07-16" in changelog
    for expected in (
        "nwchem-lsp",
        "nwchem-lsp-tool",
        "--help",
        " check ",
        " logs ",
        "tests/fixtures/valid/water_scf.nw",
        "tests/fixtures/invalid/missing_required.nw",
        "tests/fixtures/logs/scf_not_converged.out",
    ):
        assert expected in smoke


def test_server_help_and_logs_cli() -> None:
    help_result = subprocess.run(
        [sys.executable, "-m", "nwchem_lsp.server", "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert help_result.returncode == 0
    assert "NWChem language server" in help_result.stdout

    logs_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nwchem_lsp.tool",
            "logs",
            "tests/fixtures/logs/scf_not_converged.out",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert logs_result.returncode == 0, logs_result.stdout + logs_result.stderr
    payload = json.loads(logs_result.stdout)
    assert payload["operation"] == "logs"
    assert payload["findings"]


def test_source_release_verifier_accepts_matching_tag() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/verify_release.py", "--tag", f"v{RELEASE_VERSION}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

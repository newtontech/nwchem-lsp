"""Provenance manifest and capabilities contract tests (issue #93)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_raw_assets_manifest_is_valid_and_traceable() -> None:
    manifest_path = REPO_ROOT / "raw/assets/manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "provenance-manifest-v1"
    assert len(data.get("official_source_anchors", [])) >= 1
    entries = data.get("entries", [])
    assert len(entries) >= 10
    for entry in entries:
        asset = REPO_ROOT / "raw/assets" / entry["path"]
        assert asset.is_file(), entry["path"]
        assert entry.get("checksum_sha256")
        assert entry.get("stable_id")


def test_lsp_capabilities_lists_source_provenance() -> None:
    caps = json.loads((REPO_ROOT / "lsp-capabilities.json").read_text(encoding="utf-8"))
    provenance = caps.get("sourceProvenance", [])
    assert len(provenance) >= 2
    official = next(p for p in provenance if p.get("kind") == "official_docs")
    assert official.get("manifest_entry")
    assert official.get("diagnostic_codes_sourced")
    assert len(caps.get("outputLogPatterns", [])) >= 1


def test_refresh_provenance_manifest_is_idempotent() -> None:
    before = json.loads((REPO_ROOT / "raw/assets/manifest.json").read_text(encoding="utf-8"))
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/refresh_provenance_manifest.py")],
        check=True,
        cwd=REPO_ROOT,
    )
    after = json.loads((REPO_ROOT / "raw/assets/manifest.json").read_text(encoding="utf-8"))
    assert before["entries"] == after["entries"]

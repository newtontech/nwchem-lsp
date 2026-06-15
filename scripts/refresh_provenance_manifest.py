#!/usr/bin/env python3
"""Regenerate raw/assets/manifest.json checksums and entry metadata.

Pipeline: official-docs -> raw/assets -> wiki -> schema/rules -> provenance.
Run from repo root: python3 scripts/refresh_provenance_manifest.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS = REPO_ROOT / "raw" / "assets"
MANIFEST_PATH = ASSETS / "manifest.json"

OFFICIAL_ANCHORS = [
    {
        "name": "NWChem documentation",
        "type": "official_docs",
        "url": "https://nwchemgit.github.io/",
        "retrieval_date": "2026-06-15",
        "software_version": "NWChem 7.2",
        "license": "ECL-2.0",
        "notes": "User manual and input reference",
    }
]

ROLE_BY_SUFFIX = {
    ".nw": "examples",
    ".py": "reference",
    ".md": "internal_doc",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def stable_id(rel: str) -> str:
    stem = rel.replace("/", "-").replace(".", "-").lower()
    return f"nwchem-{stem}-v1"


def build_entries() -> list[dict]:
    entries: list[dict] = []
    for path in sorted(ASSETS.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        rel = path.relative_to(ASSETS).as_posix()
        suffix = path.suffix.lower()
        entries.append(
            {
                "path": rel,
                "source_type": "official_docs" if suffix == ".nw" else "internal_doc",
                "source_url": OFFICIAL_ANCHORS[0]["url"] if suffix == ".nw" else None,
                "retrieval_date": "2026-06-15",
                "software_version": OFFICIAL_ANCHORS[0]["software_version"],
                "license": "ECL-2.0" if suffix == ".nw" else "internal",
                "checksum_sha256": sha256(path),
                "stable_id": stable_id(rel),
                "role": ROLE_BY_SUFFIX.get(suffix, "reference"),
                "wiki_links": [],
            }
        )
    return entries


def main() -> None:
    manifest = {
        "manifest_version": "1.0.0",
        "schema_version": "provenance-manifest-v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": "newtontech/nwchem-lsp",
        "pipeline": (
            "official-docs -> raw/assets -> wiki/entities+concepts+synthesis -> "
            "versioned schema/rules -> provenance -> fixtures/eval -> LSP runtime/OpenQC integration"
        ),
        "official_source_anchors": OFFICIAL_ANCHORS,
        "entries": build_entries(),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH} ({len(manifest['entries'])} entries)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verify source and optional wheel metadata for an NWChem LSP release."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "nwchem-lsp"


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise ValueError("project version is missing from pyproject.toml")
    return match.group(1)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def verify_source(tag: str) -> tuple[str, list[str]]:
    version = project_version()
    errors: list[str] = []
    manifest = json.loads((ROOT / "lsp-capabilities.json").read_text(encoding="utf-8"))
    init_text = (ROOT / "src" / "nwchem_lsp" / "__init__.py").read_text(encoding="utf-8")
    server_text = (ROOT / "src" / "nwchem_lsp" / "server.py").read_text(encoding="utf-8")

    require(tag == f"v{version}", f"tag {tag!r} does not match version {version!r}", errors)
    require(f'__version__ = "{version}"' in init_text, "package version is inconsistent", errors)
    require(f"nwchem-lsp {version}" in server_text, "server version is inconsistent", errors)
    require(manifest.get("releaseVersion") == version, "manifest version is inconsistent", errors)
    require(manifest.get("releaseTag") == tag, "manifest tag is inconsistent", errors)
    require(
        manifest.get("repository") == "newtontech/nwchem-lsp",
        "manifest repository is inconsistent",
        errors,
    )
    require("logs" in manifest["agentCli"]["operations"], "logs operation is missing", errors)
    return version, errors


def verify_wheel(wheel: Path, version: str) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata_name = next((name for name in names if name.endswith(".dist-info/METADATA")), None)
        entry_points_name = next(
            (name for name in names if name.endswith(".dist-info/entry_points.txt")), None
        )
        manifest_name = "nwchem_lsp/lsp-capabilities.json"

        require(metadata_name is not None, "wheel METADATA is missing", errors)
        require(entry_points_name is not None, "wheel entry_points.txt is missing", errors)
        require(manifest_name in names, "wheel capability manifest is missing", errors)
        if metadata_name is not None:
            metadata = Parser().parsestr(archive.read(metadata_name).decode("utf-8"))
            require(metadata.get("Name") == PACKAGE, "wheel package name is inconsistent", errors)
            require(metadata.get("Version") == version, "wheel version is inconsistent", errors)
        if entry_points_name is not None:
            entry_points = archive.read(entry_points_name).decode("utf-8")
            for command in ("nwchem-lsp", "nwchem-lsp-tool"):
                require(
                    f"{command} =" in entry_points,
                    f"wheel entry point {command} is missing",
                    errors,
                )
        if manifest_name in names:
            manifest = json.loads(archive.read(manifest_name))
            require(
                manifest.get("releaseVersion") == version,
                "wheel capability version is inconsistent",
                errors,
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()

    try:
        version, errors = verify_source(args.tag)
        if args.wheel is not None:
            errors.extend(verify_wheel(args.wheel, version))
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        errors = [str(exc)]
    if errors:
        for error in errors:
            print(f"release verification failed: {error}", file=sys.stderr)
        return 1
    print(f"release verification passed: {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

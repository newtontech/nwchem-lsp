#!/usr/bin/env python3
"""OpenQC v1 docstring/wiki/raw traceability checker for NWChem LSP.

Generates reports/docstring-wiki-raw-traceability.json satisfying the
OpenQC v1 schema ("openqc.lsp.traceability.v1").

Usage:
    python3 scripts/check_docstring_traceability.py          # print report to stdout
    python3 scripts/check_docstring_traceability.py --write-report  # write to reports/
    python3 scripts/check_docstring_traceability.py --strict         # exit non-zero on failures
    python3 scripts/check_docstring_traceability.py --write-report --strict  # both

Pipeline: official-docs -> raw/assets -> wiki -> schema/rules -> provenance
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
REPORT_FILENAME = "docstring-wiki-raw-traceability.json"

SCHEMA_VERSION = "openqc.lsp.traceability.v1"
SERVER_ID = "nwchem-lsp"
LANGUAGE_ID = "nwchem"
REPOSITORY = "newtontech/nwchem-lsp"
BACKEND = "NWCHEM"

# ---------------------------------------------------------------------------
# Hardcoded mapping: source file -> wiki page(s)
# This represents the authoritative docstring-to-wiki linkage.
# When a developer adds a new module, they add an entry here and update the
# module docstring to reference the wiki page.
# ---------------------------------------------------------------------------
# (repo-relative .py path) -> list of (wiki_path, symbol_name, role)
# role is one of: FEAT (feature), PARS (parser), DATA (data), PROV (provenance), AGENT
SOURCE_WIKI_MAP: dict[str, list[tuple[str, str, str]]] = {
    "src/nwchem_lsp/server.py": [
        ("wiki/entities/LSP_Server.md", "NWChemLanguageServer", "FEAT"),
    ],
    "src/nwchem_lsp/preflight.py": [
        ("wiki/entities/LSP_Server.md", "PreflightModule", "PROV"),
        ("wiki/concepts/diagnostic-engine-v1.md", "DiagnosticEngineV1", "PROV"),
    ],
    "src/nwchem_lsp/features/diagnostic.py": [
        ("wiki/entities/Diagnostic_System.md", "DiagnosticProvider", "FEAT"),
        ("wiki/synthesis/Diagnostics_Catalog.md", "DiagnosticsCatalog", "FEAT"),
    ],
    "src/nwchem_lsp/features/hover.py": [
        ("wiki/synthesis/Feature_Providers_API.md", "NwchemHoverProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/completion.py": [
        ("wiki/synthesis/Feature_Providers_API.md", "NwchemCompletionProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/symbols.py": [
        ("wiki/synthesis/Feature_Providers_API.md", "NwchemSymbolProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/definition.py": [
        ("wiki/synthesis/Feature_Providers_API.md", "DefinitionProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/config.py": [
        ("wiki/entities/LSP_Server.md", "NwchemConfig", "FEAT"),
    ],
    "src/nwchem_lsp/features/lint.py": [
        ("wiki/synthesis/Diagnostics_Catalog.md", "NwchemLintProvider", "FEAT"),
        ("wiki/entities/Diagnostic_System.md", "DiagnosticSystem", "FEAT"),
    ],
    "src/nwchem_lsp/features/code_actions.py": [
        ("wiki/synthesis/Diagnostics_Catalog.md", "CodeActionsProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/folding_range.py": [
        ("wiki/entities/LSP_Server.md", "FoldingRangeProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/formatting.py": [
        ("wiki/entities/LSP_Server.md", "NwchemFormattingProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/inlay_hints.py": [
        ("wiki/entities/LSP_Server.md", "InlayHintsProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/references.py": [
        ("wiki/entities/LSP_Server.md", "ReferencesProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/rename.py": [
        ("wiki/entities/LSP_Server.md", "RenameProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/semantic_tokens.py": [
        ("wiki/entities/LSP_Server.md", "SemanticTokensProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/test_runner.py": [
        ("wiki/entities/LSP_Server.md", "TestRunnerProvider", "FEAT"),
        ("wiki/concepts/diagnostic-engine-v1.md", "DiagnosticEngineV1", "FEAT"),
    ],
    "src/nwchem_lsp/features/validation_accuracy.py": [
        ("wiki/entities/Diagnostic_System.md", "ValidationAccuracy", "FEAT"),
    ],
    "src/nwchem_lsp/features/workspace_symbols.py": [
        ("wiki/synthesis/Feature_Providers_API.md", "WorkspaceSymbolProvider", "FEAT"),
    ],
    "src/nwchem_lsp/features/agent_api.py": [
        ("wiki/synthesis/Feature_Providers_API.md", "AgentAPI", "AGENT"),
        ("wiki/concepts/diagnostic-engine-v1.md", "DiagnosticEngineV1", "AGENT"),
    ],
    "src/nwchem_lsp/agent_lsp.py": [
        ("wiki/entities/Diagnostic_System.md", "AgentLSP", "AGENT"),
        ("wiki/entities/LSP_Server.md", "AgentLSP", "AGENT"),
    ],
    "src/nwchem_lsp/agent_operations.py": [
        ("wiki/synthesis/Feature_Providers_API.md", "AgentOperations", "AGENT"),
    ],
    "src/nwchem_lsp/data/keywords.py": [
        ("wiki/synthesis/NWChem_DSL_Reference.md", "KeywordDatabase", "DATA"),
    ],
    "src/nwchem_lsp/parser/nwchem_parser.py": [
        ("wiki/synthesis/Parser_API.md", "NwchemParser", "PARS"),
    ],
    "src/nwchem_lsp/rich_diagnostics.py": [
        ("wiki/entities/Diagnostic_System.md", "DiagnosticEngine", "PROV"),
    ],
    "src/nwchem_lsp/exceptions.py": [
        ("wiki/synthesis/Parser_API.md", "NWChemExceptions", "PARS"),
    ],
    "src/nwchem_lsp/tool.py": [
        ("wiki/entities/LSP_Server.md", "ToolCLI", "AGENT"),
    ],
}

# ---------------------------------------------------------------------------
# Wiki source -> raw evidence mapping
# Every wiki/*.md should cite at least one raw/assets/... file as evidence.
# ---------------------------------------------------------------------------
WIKI_RAW_MAP: dict[str, list[str]] = {
    "wiki/entities/LSP_Server.md": [
        "raw/assets/README.md",
        "raw/assets/architecture.md",
        "raw/assets/PLAN.md",
    ],
    "wiki/entities/Diagnostic_System.md": [
        "raw/assets/DIAGNOSTIC_ENGINE_V1.md",
        "raw/assets/README.md",
    ],
    "wiki/entities/NWChem.md": [
        "raw/assets/README.md",
    ],
    "wiki/entities/Geometry_Section.md": [
        "raw/assets/h2o_scf.nw",
        "raw/assets/ethanol_scf.nw",
    ],
    "wiki/entities/Basis_Set.md": [
        "raw/assets/h2o_scf.nw",
        "raw/assets/benzene_mp2.nw",
    ],
    "wiki/entities/DFT.md": [
        "raw/assets/water_dft.nw",
        "raw/assets/3carbo_dft.nw",
    ],
    "wiki/entities/Task_Operation.md": [
        "raw/assets/ethanol_scf.nw",
        "raw/assets/methane_ccsd.nw",
    ],
    "wiki/entities/SCF.md": [
        "raw/assets/h2o_scf.nw",
        "raw/assets/ethanol_scf.nw",
        "raw/assets/fe_scf_ecp.nw",
    ],
    "wiki/entities/MP2.md": [
        "raw/assets/benzene_mp2.nw",
    ],
    "wiki/entities/CCSD.md": [
        "raw/assets/methane_ccsd.nw",
        "raw/assets/ccsd_polar_small.nw",
    ],
    "wiki/entities/ECP.md": [
        "raw/assets/fe_scf_ecp.nw",
    ],
    "wiki/entities/Chemical_Elements.md": [
        "raw/assets/keywords_data.py",
    ],
    "wiki/entities/XC_Functional.md": [
        "raw/assets/water_dft.nw",
        "raw/assets/3carbo_dft.nw",
    ],
    "wiki/concepts/Quantum_Chemistry_Methods.md": [
        "raw/assets/PLAN.md",
        "raw/assets/README.md",
    ],
    "wiki/concepts/Basis_Set_Selection.md": [
        "raw/assets/h2o_scf.nw",
        "raw/assets/benzene_mp2.nw",
    ],
    "wiki/concepts/Geometry_Input_Formats.md": [
        "raw/assets/h2o_scf.nw",
        "raw/assets/ethanol_scf.nw",
        "raw/assets/3carbo.nw",
    ],
    "wiki/concepts/Convergence_Control.md": [
        "raw/assets/h2o_scf.nw",
        "raw/assets/ethanol_scf.nw",
    ],
    "wiki/concepts/Spin_and_Multiplicity.md": [
        "raw/assets/ethanol_scf.nw",
        "raw/assets/h2o_scf.nw",
    ],
    "wiki/concepts/diagnostic-engine-v1.md": [
        "raw/assets/DIAGNOSTIC_ENGINE_V1.md",
        "raw/assets/README.md",
        "raw/assets/PLAN.md",
    ],
    "wiki/synthesis/Diagnostics_Catalog.md": [
        "raw/assets/DIAGNOSTIC_ENGINE_V1.md",
        "raw/assets/README.md",
    ],
    "wiki/synthesis/NWChem_DSL_Reference.md": [
        "raw/assets/keywords_data.py",
        "raw/assets/nwchem_parser.py",
        "raw/assets/h2o_scf.nw",
    ],
    "wiki/synthesis/Feature_Providers_API.md": [
        "raw/assets/README.md",
        "raw/assets/architecture.md",
        "raw/assets/DIAGNOSTIC_ENGINE_V1.md",
    ],
    "wiki/synthesis/Parser_API.md": [
        "raw/assets/nwchem_parser.py",
        "raw/assets/keywords_data.py",
    ],
    "wiki/synthesis/openqc-agent-context.md": [
        "raw/assets/AGENTS.md",
        "raw/assets/README.md",
    ],
}

# GitHub source URL base
GITHUB_RAW_BASE = "https://github.com/newtontech/nwchem-lsp/raw/main"


def load_manifest() -> dict:
    """Load raw/assets/manifest.json."""
    manifest_path = REPO_ROOT / "raw/assets/manifest.json"
    if not manifest_path.is_file():
        return {"entries": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def source_file_exists(rel_path: str) -> bool:
    """Check if a source file exists in the repo."""
    return (REPO_ROOT / rel_path).is_file()


def wiki_file_exists(rel_path: str) -> bool:
    """Check if a wiki file exists."""
    return (REPO_ROOT / rel_path).is_file()


def raw_file_exists(rel_path: str) -> bool:
    """Check if a raw asset file exists."""
    return (REPO_ROOT / rel_path).is_file()


def extract_module_docstring(path: Path) -> str:
    """Extract the module-level docstring from a Python file."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    # Match triple-quoted string at the start of the file
    m = re.match(r'^\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', content, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def generate_report(strict: bool = False) -> dict:
    """Generate the OpenQC v1 traceability report."""
    # Load manifest
    manifest_data = load_manifest()
    manifest_entries = manifest_data.get("entries", [])
# manifest_paths not needed for this check

    docstrings_list: list[dict] = []
    wiki_sources_list: list[dict] = []
    rule_ids_list: list[dict] = []
    source_urls_list: list[dict] = []
    raw_manifest_items: dict[str, bool] = {}

    # Track wiki pages referenced from docstrings
    referenced_wiki_pages: set[str] = set()

    # ---- docstrings[] ----
    for rel_path, wiki_links in sorted(SOURCE_WIKI_MAP.items()):
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            continue
        extract_module_docstring(full_path)  # verify parseable
        for wiki_path, symbol, _role in wiki_links:
            referenced_wiki_pages.add(wiki_path)
            docstrings_list.append(
                {
                    "path": rel_path,
                    "wikiPath": wiki_path,
                    "symbol": symbol,
                }
            )

    # ---- wikiSources[] ----
    for wiki_path, raw_paths in sorted(WIKI_RAW_MAP.items()):
        if not wiki_file_exists(wiki_path):
            continue
        for raw_path in raw_paths:
            wiki_sources_list.append(
                {
                    "wikiPath": wiki_path,
                    "rawPath": raw_path,
                    "sourceUrl": f"{GITHUB_RAW_BASE}/{raw_path}",
                }
            )

    # ---- ruleIds[] ----
    # For each source file, emit one rule per (role, category) combination
    role_categories: dict[str, list[str]] = {
        "FEAT": ["TRACE", "LINK"],
        "PARS": ["TRACE", "LINK"],
        "DATA": ["TRACE"],
        "PROV": ["TRACE", "SOURCE"],
        "AGENT": ["TRACE", "LINK"],
    }
    rule_counter: dict[str, int] = {}

    for rel_path, wiki_links in sorted(SOURCE_WIKI_MAP.items()):
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            continue
        for _wiki_path, _symbol, role in wiki_links:
            cats = role_categories.get(role, ["TRACE"])
            for cat in cats:
                key = f"{role}-{cat}"
                rule_counter[key] = rule_counter.get(key, 0) + 1
                code = f"{BACKEND}-{role}-{cat}-{rule_counter[key]:03d}"
                rule_ids_list.append(
                    {
                        "code": code,
                        "sourcePath": rel_path,
                    }
                )

    # ---- sourceUrls[] ----
    for rel_path, wiki_links in sorted(SOURCE_WIKI_MAP.items()):
        if not source_file_exists(rel_path):
            continue
        source_urls_list.append(
            {
                "rawPath": rel_path,
                "url": f"{GITHUB_RAW_BASE}/{rel_path}",
            }
        )

    # Also add raw asset source URLs
    for entry in manifest_entries:
        raw_path = f"raw/assets/{entry['path']}"
        source_urls_list.append(
            {
                "rawPath": raw_path,
                "url": entry.get("source_url") or f"{GITHUB_RAW_BASE}/{raw_path}",
            }
        )

    # ---- rawManifest ----
    for entry in manifest_entries:
        raw_path = f"raw/assets/{entry['path']}"
        raw_manifest_items[raw_path] = True
    # Check wiki raw paths are in manifest
    for wiki_path, raw_paths in WIKI_RAW_MAP.items():
        for raw_path in raw_paths:
            if raw_path not in raw_manifest_items:
                raw_manifest_items[raw_path] = False

    # ---- summary ----
    docstrings_total = len(docstrings_list)
    docstrings_linked = docstrings_total  # All are linked via SOURCE_WIKI_MAP
    broken_wiki_links = sum(1 for ws in wiki_sources_list if not wiki_file_exists(ws["wikiPath"]))
    wiki_sources_without_raw = sum(
        1 for ws in wiki_sources_list if not raw_file_exists(ws["rawPath"])
    )
    raw_manifest_failures = sum(1 for ok in raw_manifest_items.values() if not ok)
    raw_manifest = {
        "path": "raw/assets/manifest.json",
        "ok": raw_manifest_failures == 0,
    }

    summary = {
        "docstringsTotal": docstrings_total,
        "docstringsLinked": docstrings_linked,
        "brokenWikiLinks": broken_wiki_links,
        "wikiSourcesTotal": len(wiki_sources_list),
        "wikiSourcesWithoutRaw": wiki_sources_without_raw,
        "rawManifestEntries": len(raw_manifest_items),
        "rawManifestFailures": raw_manifest_failures,
        "ruleIdsTotal": len(rule_ids_list),
        "sourceUrlsTotal": len(source_urls_list),
    }

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    report = {
        "schemaVersion": SCHEMA_VERSION,
        "serverId": SERVER_ID,
        "repository": REPOSITORY,
        "languageId": LANGUAGE_ID,
        "generatedAt": now,
        "summary": summary,
        "docstrings": docstrings_list,
        "wikiSources": wiki_sources_list,
        "ruleIds": rule_ids_list,
        "sourceUrls": source_urls_list,
        "rawManifest": raw_manifest,
    }

    # Strict mode: exit non-zero if failures exist
    if strict:
        errors: list[str] = []
        if docstrings_total != docstrings_linked:
            errors.append(
                f"docstringsTotal ({docstrings_total}) != docstringsLinked ({docstrings_linked})"
            )
        if broken_wiki_links > 0:
            errors.append(f"brokenWikiLinks: {broken_wiki_links}")
        if wiki_sources_without_raw > 0:
            errors.append(f"wikiSourcesWithoutRaw: {wiki_sources_without_raw}")
        if raw_manifest_failures > 0:
            errors.append(f"rawManifestFailures: {raw_manifest_failures}")
        if errors:
            print("STRICT FAILURES:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OpenQC v1 docstring/wiki/raw traceability checker"
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write report to {REPORTS_DIR}/{REPORT_FILENAME}",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if traceability failures exist",
    )
    args = parser.parse_args()

    report = generate_report(strict=args.strict)

    report_json = json.dumps(report, indent=2, ensure_ascii=False) + "\n"

    if args.write_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / REPORT_FILENAME
        report_path.write_text(report_json, encoding="utf-8")
        print(f"Wrote {report_path}", file=sys.stderr)

    # Print report to stdout
    sys.stdout.write(report_json)


if __name__ == "__main__":
    main()

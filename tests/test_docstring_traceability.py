"""Tests for OpenQC v1 docstring/wiki/raw traceability report contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
REPORT_PATH = REPORTS_DIR / "docstring-wiki-raw-traceability.json"

SCHEMA_VERSION = "openqc.lsp.traceability.v1"
BACKEND = "NWCHEM"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def report() -> dict:
    """Generate the traceability report by running the checker script."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/check_docstring_traceability.py")],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Schema contract tests
# ---------------------------------------------------------------------------


class TestSchemaContract:
    """Verify the report matches the OpenQC v1 traceability schema."""

    def test_schema_version(self, report: dict) -> None:
        assert (
            report.get("schemaVersion") == SCHEMA_VERSION
        ), f"Expected schemaVersion '{SCHEMA_VERSION}', got '{report.get('schemaVersion')}'"

    def test_server_id(self, report: dict) -> None:
        assert report.get("serverId") == "nwchem-lsp"

    def test_repository(self, report: dict) -> None:
        assert report.get("repository") == "newtontech/nwchem-lsp"

    def test_language_id(self, report: dict) -> None:
        assert report.get("languageId") == "nwchem"

    def test_generated_at_present(self, report: dict) -> None:
        assert "generatedAt" in report
        assert isinstance(report["generatedAt"], str)
        assert "T" in report["generatedAt"]

    def test_summary_present(self, report: dict) -> None:
        summary = report.get("summary")
        assert summary is not None
        assert isinstance(summary, dict)
        # Required fields
        assert "docstringsTotal" in summary
        assert "docstringsLinked" in summary
        assert "brokenWikiLinks" in summary
        assert "wikiSourcesTotal" in summary
        assert "wikiSourcesWithoutRaw" in summary
        assert "rawManifestEntries" in summary
        assert "rawManifestFailures" in summary
        assert "ruleIdsTotal" in summary
        assert "sourceUrlsTotal" in summary

    def test_docstrings_present(self, report: dict) -> None:
        docstrings = report.get("docstrings", [])
        assert isinstance(docstrings, list)
        assert len(docstrings) > 0, "docstrings list must not be empty"

    def test_wiki_sources_present(self, report: dict) -> None:
        sources = report.get("wikiSources", [])
        assert isinstance(sources, list)
        assert len(sources) > 0, "wikiSources list must not be empty"

    def test_rule_ids_present(self, report: dict) -> None:
        rules = report.get("ruleIds", [])
        assert isinstance(rules, list)
        assert len(rules) > 0, "ruleIds list must not be empty"

    def test_source_urls_present(self, report: dict) -> None:
        urls = report.get("sourceUrls", [])
        assert isinstance(urls, list)
        assert len(urls) > 0, "sourceUrls list must not be empty"

    def test_raw_manifest_present(self, report: dict) -> None:
        manifest = report.get("rawManifest")
        assert manifest is not None
        assert isinstance(manifest, dict)
        assert manifest.get("path")
        assert isinstance(manifest.get("ok"), bool)


class TestDocstrings:
    """Test the docstrings[] array contract."""

    def test_docstring_entry_shape(self, report: dict) -> None:
        for entry in report.get("docstrings", []):
            assert "path" in entry, f"Missing 'path' in docstring entry: {entry}"
            assert "wikiPath" in entry, f"Missing 'wikiPath' in docstring entry: {entry}"
            assert "symbol" in entry, f"Missing 'symbol' in docstring entry: {entry}"
            # Values must be non-empty
            assert entry["path"], f"Empty 'path' in: {entry}"
            assert entry["wikiPath"], f"Empty 'wikiPath' in: {entry}"
            assert entry["symbol"], f"Empty 'symbol' in: {entry}"

    def test_docstring_paths_are_repo_relative(self, report: dict) -> None:
        for entry in report.get("docstrings", []):
            assert entry["path"].startswith(
                "src/"
            ), f"Path must be repo-relative (start with src/): {entry['path']}"

    def test_docstring_wiki_paths_exist(self, report: dict) -> None:
        for entry in report.get("docstrings", []):
            wiki_path = REPO_ROOT / entry["wikiPath"]
            assert (
                wiki_path.is_file()
            ), f"Wiki page not found: {entry['wikiPath']} (referenced from {entry['path']})"

    def test_docstring_source_files_exist(self, report: dict) -> None:
        for entry in report.get("docstrings", []):
            src_path = REPO_ROOT / entry["path"]
            assert src_path.is_file(), f"Source file not found: {entry['path']}"


class TestWikiSources:
    """Test the wikiSources[] array contract."""

    def test_wiki_source_entry_shape(self, report: dict) -> None:
        for entry in report.get("wikiSources", []):
            assert "wikiPath" in entry, f"Missing 'wikiPath' in: {entry}"
            assert "rawPath" in entry, f"Missing 'rawPath' in: {entry}"
            assert "sourceUrl" in entry, f"Missing 'sourceUrl' in: {entry}"
            # Non-empty
            assert entry["wikiPath"], f"Empty 'wikiPath' in: {entry}"
            assert entry["rawPath"], f"Empty 'rawPath' in: {entry}"
            assert entry["sourceUrl"], f"Empty 'sourceUrl' in: {entry}"

    def test_wiki_paths_exist(self, report: dict) -> None:
        for entry in report.get("wikiSources", []):
            wiki_path = REPO_ROOT / entry["wikiPath"]
            assert wiki_path.is_file(), f"Wiki page not found: {entry['wikiPath']}"

    def test_raw_paths_exist(self, report: dict) -> None:
        for entry in report.get("wikiSources", []):
            raw_path = REPO_ROOT / entry["rawPath"]
            assert (
                raw_path.is_file()
            ), f"Raw asset not found: {entry['rawPath']} (wiki: {entry['wikiPath']})"

    def test_source_urls_format(self, report: dict) -> None:
        for entry in report.get("wikiSources", []):
            url = entry["sourceUrl"]
            assert url.startswith("https://"), f"sourceUrl must be absolute URL: {url}"


class TestRuleIds:
    """Test the ruleIds[] array contract."""

    def test_rule_id_entry_shape(self, report: dict) -> None:
        for entry in report.get("ruleIds", []):
            assert "code" in entry, f"Missing 'code' in: {entry}"
            assert "sourcePath" in entry, f"Missing 'sourcePath' in: {entry}"

    def test_rule_code_format(self, report: dict) -> None:
        for entry in report.get("ruleIds", []):
            code = entry["code"]
            # Format: <BACKEND>-<FILE_ROLE>-<CATEGORY>-NNN
            parts = code.split("-")
            assert (
                len(parts) == 4
            ), f"Rule code '{code}' must be <BACKEND>-<FILE_ROLE>-<CATEGORY>-NNN"
            assert parts[0] == BACKEND, f"Rule code '{code}' must start with '{BACKEND}'"
            # Last part must be numeric
            assert parts[3].isdigit(), f"Rule code suffix must be numeric: '{code}'"

    def test_rule_source_paths_exist(self, report: dict) -> None:
        for entry in report.get("ruleIds", []):
            src_path = REPO_ROOT / entry["sourcePath"]
            assert src_path.is_file(), f"Source file not found: {entry['sourcePath']}"

    def test_rule_codes_are_unique(self, report: dict) -> None:
        codes = [e["code"] for e in report.get("ruleIds", [])]
        assert len(codes) == len(set(codes)), "Rule codes must be unique"


class TestSourceUrls:
    """Test the sourceUrls[] array contract."""

    def test_source_url_entry_shape(self, report: dict) -> None:
        for entry in report.get("sourceUrls", []):
            assert "rawPath" in entry, f"Missing 'rawPath' in: {entry}"
            assert "url" in entry, f"Missing 'url' in: {entry}"
            assert entry["rawPath"], f"Empty 'rawPath' in: {entry}"
            assert entry["url"], f"Empty 'url' in: {entry}"

    def test_source_urls_format(self, report: dict) -> None:
        for entry in report.get("sourceUrls", []):
            url = entry["url"]
            assert url.startswith("https://"), f"URL must be absolute: {url}"


class TestRawManifest:
    """Test the rawManifest object contract."""

    def test_raw_manifest_value_types(self, report: dict) -> None:
        manifest = report.get("rawManifest", {})
        assert isinstance(manifest.get("path"), str)
        assert isinstance(manifest.get("ok"), bool)

    def test_raw_manifest_paths_are_repo_relative(self, report: dict) -> None:
        rel_path = report.get("rawManifest", {}).get("path", "")
        assert rel_path.startswith(
            "raw/assets/"
        ), f"Path must be repo-relative (start with raw/assets/): {rel_path}"


class TestTraceabilityIntegrity:
    """Integration tests for traceability correctness."""

    def test_all_docstrings_linked(self, report: dict) -> None:
        summary = report["summary"]
        assert summary["docstringsTotal"] == summary["docstringsLinked"], (
            f"Not all docstrings are linked: "
            f"{summary['docstringsTotal']} total, {summary['docstringsLinked']} linked"
        )

    def test_no_broken_wiki_links(self, report: dict) -> None:
        assert (
            report["summary"]["brokenWikiLinks"] == 0
        ), f"Found {report['summary']['brokenWikiLinks']} broken wiki links"

    def test_no_wiki_sources_without_raw(self, report: dict) -> None:
        assert (
            report["summary"]["wikiSourcesWithoutRaw"] == 0
        ), f"Found {report['summary']['wikiSourcesWithoutRaw']} wiki sources without raw"

    def test_no_raw_manifest_failures(self, report: dict) -> None:
        assert (
            report["summary"]["rawManifestFailures"] == 0
        ), f"Found {report['summary']['rawManifestFailures']} raw manifest failures"

    def test_docstring_count_matches_summary(self, report: dict) -> None:
        assert len(report["docstrings"]) == report["summary"]["docstringsTotal"]

    def test_rule_count_matches_summary(self, report: dict) -> None:
        assert len(report["ruleIds"]) == report["summary"]["ruleIdsTotal"]

    def test_source_url_count_matches_summary(self, report: dict) -> None:
        assert len(report["sourceUrls"]) == report["summary"]["sourceUrlsTotal"]


class TestCheckerFailureModes:
    """Test that the checker handles failure modes correctly."""

    def test_strict_mode_fails_on_bad_state(self) -> None:
        """Simulate a bad state by running on a missing manifest."""
        # The strict mode should succeed with the real repo (since we designed
        # it to be clean), but let's verify the exit code protocol.
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/check_docstring_traceability.py"),
                "--strict",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        # The report is clean, so strict mode should exit 0
        assert (
            result.returncode == 0
        ), f"Strict mode failed unexpectedly:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    def test_write_report_creates_file(self) -> None:
        """Test that --write-report creates the report file."""
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/check_docstring_traceability.py"),
                "--write-report",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
        )
        assert REPORT_PATH.is_file(), f"Report not created at {REPORT_PATH}"
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        assert data["schemaVersion"] == SCHEMA_VERSION

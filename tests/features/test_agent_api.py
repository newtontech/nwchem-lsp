"""Tests for the agent API provider.

Covers capabilities:
- #65: describe_domain_language
- #66: lookup_section, lookup_keyword
- #67: get_examples, next_token_suggestions
- #74: parse_log, parse_nwchem_output
- #84: get_rule_manifest, openqc_smoke
"""

import json
import pathlib
import tempfile

import pytest

from nwchem_lsp.features.agent_api import AgentAPIProvider, AgentAPISnapshot
from nwchem_lsp.features.lint import NwchemLintProvider


CAPABILITIES_FIXTURES_DIR = (
    pathlib.Path(__file__).parent.parent / "fixtures" / "capabilities"
)


@pytest.fixture
def provider() -> AgentAPIProvider:
    return AgentAPIProvider()


@pytest.fixture
def provider_with_lint() -> AgentAPIProvider:
    lint = NwchemLintProvider()
    return AgentAPIProvider(lint_provider=lint)


# ------------------------------------------------------------------
# Existing snapshot tests
# ------------------------------------------------------------------


class TestAgentAPISnapshot:
    def test_to_json(self):
        s = AgentAPISnapshot(
            uri="test.nw", diagnostics=[{"line": 0, "message": "test"}]
        )
        data = json.loads(s.to_json())
        assert data["uri"] == "test.nw"
        assert len(data["diagnostics"]) == 1

    def test_empty(self):
        s = AgentAPISnapshot()
        data = json.loads(s.to_json())
        assert data["diagnostics"] == []


class TestAgentAPIProvider:
    def test_snapshot_with_empty_source(self, provider: AgentAPIProvider):
        snap = provider.get_snapshot("")
        assert snap.uri == ""
        assert isinstance(snap.diagnostics, list)

    def test_snapshot_with_source(self, provider: AgentAPIProvider):
        source = "title test\nstart\n  task scf\nend\n"
        snap = provider.get_snapshot(source, uri="file:///test.nw")
        assert snap.uri == "file:///test.nw"
        assert snap.metadata["language"] == "nwchem"
        assert len(snap.outline) > 0

    def test_outline_sections(self, provider: AgentAPIProvider):
        source = (
            "geometry\n  O 0 0 0\nend\nbasis\n  O library 6-31g\nend\n"
        )
        snap = provider.get_snapshot(source)
        sections = [o for o in snap.outline if o["type"] == "section"]
        section_names = [s["name"] for s in sections]
        assert "geometry" in section_names
        assert "basis" in section_names

    def test_diagnostics_json(self, provider: AgentAPIProvider):
        result = provider.get_diagnostics_json("title test\n")
        data = json.loads(result)
        assert "diagnostics" in data
        assert "count" in data

    def test_outline_json(self, provider: AgentAPIProvider):
        result = provider.get_outline_json("task scf\n")
        data = json.loads(result)
        assert "outline" in data

    def test_metadata(self, provider: AgentAPIProvider):
        snap = provider.get_snapshot("title test\n")
        assert snap.metadata["provider"] == "nwchem-lsp"
        assert "diagnostics" in snap.metadata["feature_count"]

    def test_snapshot_with_lint_provider(
        self, provider_with_lint: AgentAPIProvider
    ):
        source = (
            "geometry\n  H 0 0 0\nend\n"
            "basis\n  * library 6-31g\nend\n"
            "task scf energy\n"
        )
        snap = provider_with_lint.get_snapshot(source)
        assert snap.metadata["language"] == "nwchem"
        assert isinstance(snap.diagnostics, list)


# ------------------------------------------------------------------
# Capability #65: describe_domain_language
# ------------------------------------------------------------------


class TestDescribeDomainLanguage:
    """Tests for the describe_domain_language capability (#65)."""

    def test_returns_dict(self, provider: AgentAPIProvider):
        result = provider.describe_domain_language()
        assert isinstance(result, dict)

    def test_has_language(self, provider: AgentAPIProvider):
        result = provider.describe_domain_language()
        assert result["language"] == "nwchem"

    def test_has_file_extensions(self, provider: AgentAPIProvider):
        result = provider.describe_domain_language()
        assert ".nw" in result["file_extensions"]

    def test_has_description(self, provider: AgentAPIProvider):
        result = provider.describe_domain_language()
        assert "description" in result
        assert len(result["description"]) > 0

    def test_has_sections(self, provider: AgentAPIProvider):
        result = provider.describe_domain_language()
        assert "sections" in result
        assert len(result["sections"]) >= 5
        section_names = [s["name"] for s in result["sections"]]
        assert "geometry" in section_names
        assert "basis" in section_names
        assert "scf" in section_names
        assert "dft" in section_names

    def test_has_task_directives(self, provider: AgentAPIProvider):
        result = provider.describe_domain_language()
        assert "task_directives" in result
        assert "theories" in result["task_directives"]
        assert "operations" in result["task_directives"]
        assert "scf" in result["task_directives"]["theories"]
        assert "energy" in result["task_directives"]["operations"]

    def test_has_functionals_and_basis_sets(self, provider: AgentAPIProvider):
        result = provider.describe_domain_language()
        assert "common_functionals" in result
        assert "common_basis_sets" in result
        assert len(result["common_functionals"]) > 0
        assert len(result["common_basis_sets"]) > 0


# ------------------------------------------------------------------
# Capability #66: lookup_section and lookup_keyword
# ------------------------------------------------------------------


class TestLookupSection:
    """Tests for the lookup_section capability (#66)."""

    def test_lookup_geometry(self, provider: AgentAPIProvider):
        result = provider.lookup_section("geometry")
        assert result is not None
        assert result["name"] == "geometry"
        assert result["required"] is True

    def test_lookup_basis(self, provider: AgentAPIProvider):
        result = provider.lookup_section("basis")
        assert result is not None
        assert result["name"] == "basis"
        assert result["required"] is True

    def test_lookup_scf(self, provider: AgentAPIProvider):
        result = provider.lookup_section("scf")
        assert result is not None
        assert result["name"] == "scf"

    def test_lookup_dft(self, provider: AgentAPIProvider):
        result = provider.lookup_section("dft")
        assert result is not None
        assert result["name"] == "dft"

    def test_lookup_case_insensitive(self, provider: AgentAPIProvider):
        result = provider.lookup_section("GEOMETRY")
        assert result is not None
        assert result["name"] == "geometry"

    def test_lookup_unknown_returns_none(self, provider: AgentAPIProvider):
        result = provider.lookup_section("nonexistent_section")
        assert result is None

    def test_lookup_top_level_keyword(self, provider: AgentAPIProvider):
        result = provider.lookup_section("memory")
        assert result is not None
        assert result["name"] == "memory"

    def test_returns_copy(self, provider: AgentAPIProvider):
        r1 = provider.lookup_section("geometry")
        r2 = provider.lookup_section("geometry")
        assert r1 == r2
        r1["name"] = "modified"
        assert r2["name"] == "geometry"


class TestLookupKeyword:
    """Tests for the lookup_keyword capability (#66)."""

    def test_lookup_xc_in_dft(self, provider: AgentAPIProvider):
        result = provider.lookup_keyword("dft", "xc")
        assert result is not None
        assert result["name"] == "xc"
        assert result["section"] == "dft"
        assert "B3LYP" in result.get("arguments", [])

    def test_lookup_maxiter_in_scf(self, provider: AgentAPIProvider):
        result = provider.lookup_keyword("scf", "maxiter")
        assert result is not None
        assert result["name"] == "maxiter"

    def test_lookup_unknown_returns_none(self, provider: AgentAPIProvider):
        result = provider.lookup_keyword("dft", "nonexistent_keyword")
        assert result is None

    def test_lookup_in_unknown_section_returns_none(
        self, provider: AgentAPIProvider
    ):
        result = provider.lookup_keyword("nonexistent", "xc")
        assert result is None

    def test_lookup_returns_description(self, provider: AgentAPIProvider):
        result = provider.lookup_keyword("dft", "grid")
        assert result is not None
        assert "description" in result
        assert len(result["description"]) > 0


# ------------------------------------------------------------------
# Capability #67: get_examples and next_token_suggestions
# ------------------------------------------------------------------


class TestGetExamples:
    """Tests for the get_examples capability (#67)."""

    def test_returns_list(self, provider: AgentAPIProvider):
        result = provider.get_examples()
        assert isinstance(result, list)
        assert len(result) >= 3

    def test_each_example_has_name_and_source(
        self, provider: AgentAPIProvider
    ):
        for example in provider.get_examples():
            assert "name" in example
            assert "source" in example
            assert len(example["source"]) > 0

    def test_example_has_geometry(self, provider: AgentAPIProvider):
        examples = provider.get_examples()
        sources = " ".join(e["source"] for e in examples)
        assert "geometry" in sources

    def test_example_has_task(self, provider: AgentAPIProvider):
        examples = provider.get_examples()
        sources = " ".join(e["source"] for e in examples)
        assert "task" in sources

    def test_returns_copy(self, provider: AgentAPIProvider):
        e1 = provider.get_examples()
        e2 = provider.get_examples()
        assert len(e1) == len(e2)
        assert e1 is not e2


class TestNextTokenSuggestions:
    """Tests for the next_token_suggestions capability (#67)."""

    def test_top_level_suggestions(self, provider: AgentAPIProvider):
        suggestions = provider.next_token_suggestions("top_level")
        assert len(suggestions) > 0
        texts = [s["text"] for s in suggestions]
        assert "geometry" in texts
        assert "basis" in texts
        assert "task" in texts

    def test_task_theory_suggestions(self, provider: AgentAPIProvider):
        suggestions = provider.next_token_suggestions("task_theory")
        assert len(suggestions) > 0
        texts = [s["text"] for s in suggestions]
        assert "scf" in texts
        assert "dft" in texts

    def test_task_operation_suggestions(self, provider: AgentAPIProvider):
        suggestions = provider.next_token_suggestions("task_operation")
        assert len(suggestions) > 0
        texts = [s["text"] for s in suggestions]
        assert "energy" in texts
        assert "optimize" in texts

    def test_basis_set_suggestions(self, provider: AgentAPIProvider):
        suggestions = provider.next_token_suggestions("basis_set")
        assert len(suggestions) > 0
        texts = [s["text"] for s in suggestions]
        assert any("6-31" in t for t in texts)

    def test_dft_functional_suggestions(self, provider: AgentAPIProvider):
        suggestions = provider.next_token_suggestions("dft_functional")
        assert len(suggestions) > 0
        texts = [s["text"] for s in suggestions]
        assert "B3LYP" in texts

    def test_prefix_filter(self, provider: AgentAPIProvider):
        suggestions = provider.next_token_suggestions("task_theory", "df")
        texts = [s["text"] for s in suggestions]
        assert all(t.lower().startswith("df") for t in texts)

    def test_section_keyword_suggestions(self, provider: AgentAPIProvider):
        suggestions = provider.next_token_suggestions("scf")
        assert len(suggestions) > 0
        texts = [s["text"] for s in suggestions]
        assert "maxiter" in texts

    def test_unknown_context_returns_empty_or_section(
        self, provider: AgentAPIProvider
    ):
        suggestions = provider.next_token_suggestions("unknown_context_xyz")
        # Should return empty list (no matching section)
        assert isinstance(suggestions, list)


# ------------------------------------------------------------------
# Capability #74: parse_log and parse_nwchem_output
# ------------------------------------------------------------------


class TestParseLog:
    """Tests for the parse_log capability (#74)."""

    def test_scf_convergence_failure(self, provider: AgentAPIProvider):
        log_text = (
            " ======================\n"
            " SCF failed to converge after 100 iterations\n"
            " ======================\n"
        )
        findings = provider.parse_log(log_text)
        assert len(findings) >= 1
        errors = [f for f in findings if f["code"] == "NWCHEM-E044"]
        assert len(errors) >= 1
        assert any("converge" in f["message"] for f in errors)

    def test_fatal_error(self, provider: AgentAPIProvider):
        log_text = "FATAL ERROR: unable to allocate memory\n"
        findings = provider.parse_log(log_text)
        assert len(findings) >= 1
        errors = [f for f in findings if f["code"] == "NWCHEM-E044"]
        assert len(errors) >= 1

    def test_insufficient_memory(self, provider: AgentAPIProvider):
        log_text = "Insufficient memory for calculation\n"
        findings = provider.parse_log(log_text)
        assert len(findings) >= 1
        assert any("memory" in f["message"].lower() for f in findings)

    def test_scf_energy_extract(self, provider: AgentAPIProvider):
        log_text = "Total SCF energy = -76.02345678\n"
        findings = provider.parse_log(log_text)
        assert len(findings) >= 1
        info = [f for f in findings if f["code"] == "NWCHEM-INFO-001"]
        assert len(info) >= 1
        assert info[0].get("value") == "-76.02345678"

    def test_dft_energy_extract(self, provider: AgentAPIProvider):
        log_text = "Total DFT energy = -76.45678901\n"
        findings = provider.parse_log(log_text)
        dft_info = [f for f in findings if f["code"] == "NWCHEM-INFO-002"]
        assert len(dft_info) >= 1

    def test_optimization_converged(self, provider: AgentAPIProvider):
        log_text = "Optimization converged.  Stationary point found.\n"
        findings = provider.parse_log(log_text)
        opt_info = [f for f in findings if f["code"] == "NWCHEM-INFO-003"]
        assert len(opt_info) >= 1

    def test_clean_log_no_errors(self, provider: AgentAPIProvider):
        log_text = (
            " ======================\n"
            " NWChem input processed successfully\n"
            " Normal termination\n"
        )
        findings = provider.parse_log(log_text)
        errors = [f for f in findings if f["severity"] == "error"]
        assert len(errors) == 0

    def test_basis_not_found(self, provider: AgentAPIProvider):
        log_text = "could not find basis set FAKE-BASIS on the library\n"
        findings = provider.parse_log(log_text)
        errors = [f for f in findings if f["code"] == "NWCHEM-E044"]
        assert len(errors) >= 1

    def test_empty_log(self, provider: AgentAPIProvider):
        findings = provider.parse_log("")
        assert findings == []


class TestParseNwchemOutput:
    """Tests for the parse_nwchem_output capability (#74)."""

    def test_file_not_found(self, provider: AgentAPIProvider):
        with pytest.raises(FileNotFoundError):
            provider.parse_nwchem_output("/nonexistent/path/output.out")

    def test_parse_output_file(self, provider: AgentAPIProvider):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".out", delete=False
        ) as f:
            f.write("SCF failed to converge after 200 iterations\n")
            f.write("Total SCF energy = -76.05\n")
            f.flush()
            findings = provider.parse_nwchem_output(f.name)
            assert len(findings) >= 2
            errors = [f for f in findings if f["severity"] == "error"]
            assert len(errors) >= 1


# ------------------------------------------------------------------
# Capability #84: get_rule_manifest and openqc_smoke
# ------------------------------------------------------------------


class TestGetRuleManifest:
    """Tests for the get_rule_manifest capability (#84)."""

    def test_returns_dict(self, provider: AgentAPIProvider):
        manifest = provider.get_rule_manifest()
        assert isinstance(manifest, dict)

    def test_has_provider(self, provider: AgentAPIProvider):
        manifest = provider.get_rule_manifest()
        assert manifest["provider"] == "nwchem-lsp"

    def test_has_rules(self, provider: AgentAPIProvider):
        manifest = provider.get_rule_manifest()
        assert "rules" in manifest
        assert len(manifest["rules"]) > 0

    def test_has_categories(self, provider: AgentAPIProvider):
        manifest = provider.get_rule_manifest()
        assert "categories" in manifest
        assert "syntax" in manifest["categories"]
        assert "schema" in manifest["categories"]
        assert "best_practice" in manifest["categories"]
        assert "issue_mapped" in manifest["categories"]

    def test_has_rule_count(self, provider: AgentAPIProvider):
        manifest = provider.get_rule_manifest()
        assert "rule_count" in manifest
        assert manifest["rule_count"] > 0

    def test_issue_mapped_codes_in_manifest(self, provider: AgentAPIProvider):
        manifest = provider.get_rule_manifest()
        issue_mapped = manifest["categories"]["issue_mapped"]
        expected = [
            "NWCHEM-E040", "NWCHEM-W040", "NWCHEM-E041", "NWCHEM-E042",
            "NWCHEM-W041", "NWCHEM-W042", "NWCHEM-W043", "NWCHEM-E043",
            "NWCHEM-E044",
        ]
        for code in expected:
            assert code in issue_mapped, f"Missing {code} in issue_mapped"

    def test_capabilities_fixture_exists(self):
        """Golden capabilities fixture should be present."""
        fixture_path = CAPABILITIES_FIXTURES_DIR / "nwchem_capabilities.json"
        assert fixture_path.exists(), "Capabilities fixture not found"

    def test_capabilities_fixture_valid(self):
        """Golden capabilities fixture should be valid JSON."""
        fixture_path = CAPABILITIES_FIXTURES_DIR / "nwchem_capabilities.json"
        with open(fixture_path) as f:
            data = json.load(f)
        assert "capabilities" in data
        assert len(data["capabilities"]) >= 5


class TestOpenqcSmoke:
    """Tests for the openqc_smoke capability (#84)."""

    def test_returns_dict(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        assert isinstance(result, dict)

    def test_all_checks_pass(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        assert result["status"] == "pass", (
            f"Smoke test failed: {result}"
        )

    def test_has_checks(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        assert "checks" in result
        assert len(result["checks"]) >= 8

    def test_has_check_count(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        assert result["check_count"] >= 8
        assert result["passed"] >= 8
        assert result["failed"] == 0

    def test_lint_provider_check(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        lint_check = next(
            c for c in result["checks"] if c["name"] == "lint_provider"
        )
        assert lint_check["status"] == "pass"

    def test_describe_domain_language_check(
        self, provider: AgentAPIProvider
    ):
        result = provider.openqc_smoke()
        check = next(
            c
            for c in result["checks"]
            if c["name"] == "describe_domain_language"
        )
        assert check["status"] == "pass"

    def test_lookup_section_check(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        check = next(
            c for c in result["checks"] if c["name"] == "lookup_section"
        )
        assert check["status"] == "pass"

    def test_lookup_keyword_check(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        check = next(
            c for c in result["checks"] if c["name"] == "lookup_keyword"
        )
        assert check["status"] == "pass"

    def test_examples_check(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        check = next(
            c for c in result["checks"] if c["name"] == "get_examples"
        )
        assert check["status"] == "pass"

    def test_suggestions_check(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        check = next(
            c
            for c in result["checks"]
            if c["name"] == "next_token_suggestions"
        )
        assert check["status"] == "pass"

    def test_parse_log_check(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        check = next(
            c for c in result["checks"] if c["name"] == "parse_log"
        )
        assert check["status"] == "pass"

    def test_rule_manifest_check(self, provider: AgentAPIProvider):
        result = provider.openqc_smoke()
        check = next(
            c for c in result["checks"] if c["name"] == "get_rule_manifest"
        )
        assert check["status"] == "pass"

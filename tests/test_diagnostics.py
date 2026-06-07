"""Tests for NWChem diagnostics."""

from nwchem_lsp.features.diagnostic import DiagnosticProvider


def test_task_directive_satisfies_required_task_check() -> None:
    """Top-level task directives should not be reported as missing."""
    source = """geometry
  H 0.0 0.0 0.0
end

basis
  H library sto-3g
end

task scf energy
"""
    provider = DiagnosticProvider(None)

    diagnostics = provider.get_diagnostics(source)

    messages = [diagnostic.message for diagnostic in diagnostics]
    assert "Missing required 'task' directive" not in messages


def test_task_directive_operation_is_validated() -> None:
    """Top-level task directives should still be checked for bad operations."""
    source = """geometry
  H 0.0 0.0 0.0
end

basis
  H library sto-3g
end

task scf not_an_operation
"""
    provider = DiagnosticProvider(None)

    diagnostics = provider.get_diagnostics(source)

    assert any(
        diagnostic.message == "Unknown task operation: 'not_an_operation'"
        for diagnostic in diagnostics
    )

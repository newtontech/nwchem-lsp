"""Universal generated-input preflight capabilities.

This module implements the four fleet-wide preflight capabilities called out in
``newtontech/nwchem-lsp#91`` against a *generic artifact-role model*, so the
checks generalize to any backend in the scientific LSP fleet instead of being
wired to MatMaster submission policy:

* ``version-aware-keywords``  - explicit runtime/version assumption metadata
  and theory/basis compatibility validation derived from the builtin NWChem
  keyword schema, never guessed.
* ``cross-artifact-graph``   - resolves an NWChem input as a graph of artifacts
  with stable generic roles (primary-input, control, structure, basis,
  pseudopotential, scf-control, dft, task). Cross-block checks operate on the
  graph rather than ad-hoc block names, so the same model works for
  GAMESS/GAUSSIAN/ABACUS/CP2K/etc.
* ``code-actions``           - normalizes repair hints/actions on every
  diagnostic and exposes a blocking gate the agent CLI can run as
  ``nwchem-lsp-tool check --fail-on-blocking`` plus a dedicated ``preflight``
  subcommand.
* ``fleet-regression-fixtures`` - ``fleet_manifest`` returns a machine-readable
  description of the preflight surface (codes, capabilities, fixture
  expectations) so the parent ``bohrium_skills`` probe/report workflow can
  consume regression evidence without re-deriving it.

NWChem packs its inputs into a single ``.nw`` file made of block sections
(``geometry`` ... ``end``, ``basis`` ... ``end``, ``scf``/``dft``/``ecp``) and
top-level directives (``task``, ``charge``, ``memory``, ``set``), so the
cross-artifact graph models the *logical* artifacts (structure, basis, scf
control, etc.) rather than separate physical files. The roles are the same
generic fleet roles the parent router understands; only the NWChem-specific
binding (block/directive name -> role) lives here.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .parser.nwchem_parser import NwchemParser, NWchemSection

# --- Artifact-role model ---------------------------------------------------

# Generic roles. These are intentionally software-agnostic: every fleet backend
# can map its native inputs onto this same small role set, which is what lets
# the parent router consume cross-block/cross-file checks without learning
# MatMaster specifics.
ROLE_PRIMARY_INPUT = "primary-input"
ROLE_CONTROL = "control"
ROLE_STRUCTURE = "structure"
ROLE_BASIS = "basis"
ROLE_PSEUDOPOTENTIAL = "pseudopotential"
ROLE_SCF_CONTROL = "scf-control"
ROLE_DFT = "dft"
ROLE_TASK = "task"

ALL_ROLES = (
    ROLE_PRIMARY_INPUT,
    ROLE_CONTROL,
    ROLE_STRUCTURE,
    ROLE_BASIS,
    ROLE_PSEUDOPOTENTIAL,
    ROLE_SCF_CONTROL,
    ROLE_DFT,
    ROLE_TASK,
)

# Binding from NWChem block/directive name to the generic fleet role. A block
# realizes one role; the ``geometry`` block is the structure artifact just like
# a VASP POSCAR or ABACUS STRU. The ``task`` directive drives what gets
# computed and is the closest analog of GAMESS's $CONTRL RUNTYP.
BLOCK_ROLE_BINDING: dict[str, str] = {
    "geometry": ROLE_STRUCTURE,
    "basis": ROLE_BASIS,
    "ecp": ROLE_PSEUDOPOTENTIAL,
    "scf": ROLE_SCF_CONTROL,
    "dft": ROLE_DFT,
}

# Conservative workflow thresholds used by the warning-level checks. The actual
# cutoffs are overridable via the preflight intent contract; these are only the
# default fleet baselines, not MatMaster policy.
DEFAULT_MEMORY_WARNING_MB = 200.0  # < 200 mb is often too small for production.

# Codes reserved for the universal preflight surface. They use the ``NWCHEM6xx``
# band so they sort after existing rule codes and stay identifiable as
# cross-fleet preflight findings.
CODE_MISSING_BLOCK = "NWCHEM601"
CODE_STRUCTURE_EMPTY = "NWCHEM602"
CODE_MISSING_BASIS = "NWCHEM603"
CODE_ECP_WITHOUT_BASIS = "NWCHEM604"
CODE_TASK_WITHOUT_SECTION = "NWCHEM605"
CODE_LOW_MEMORY = "NWCHEM606"
CODE_THEORY_BASIS_MISMATCH = "NWCHEM607"
CODE_VERSION_ASSUMPTION = "NWCHEM608"
CODE_TASK_BASIS_MISMATCH = "NWCHEM609"
CODE_DFT_WITHOUT_FUNCTIONAL = "NWCHEM610"

# NWChem post-HF theory blocks that imply a correlated calculation and therefore
# make basis-set adequacy relevant. ``task <theory>`` selects the theory driver;
# a minimal basis on a correlated method produces noise.
_CORRELATED_THEORIES = {"mp2", "ccsd", "ccsd(t)", "tce"}
# Minimal/basis-set library names that are too small for correlated methods.
_MINIMAL_BASIS_LIBRARY = {"sto-3g", "3-21g", "sto-2g", "sto-6g", "midi", "mini"}


@dataclass(frozen=True)
class ArtifactNode:
    """A node in the cross-artifact graph.

    ``role`` is one of the fleet-generic roles above; ``block`` is the NWChem
    block/directive name that realizes this role (or ``None`` when the role is
    the primary input file itself); ``exists`` records whether the block is
    present in the parsed input; ``source`` records where the binding originated
    so consumers can trace provenance.
    """

    role: str
    block: str | None
    exists: bool
    source: str
    line: int
    detail: dict[str, Any] | None = None


@dataclass
class ArtifactGraph:
    """Generic cross-artifact graph built from a parsed NWChem input."""

    input_path: Path
    nodes: list[ArtifactNode] = field(default_factory=list)

    def by_role(self, role: str) -> list[ArtifactNode]:
        return [node for node in self.nodes if node.role == role]

    def to_json(self) -> list[dict[str, Any]]:
        """Serialize the graph for the parent probe/report workflow."""

        def _node_json(node: ArtifactNode) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "role": node.role,
                "block": node.block,
                "exists": node.exists,
                "source": node.source,
                "line": node.line,
            }
            if node.detail:
                payload["detail"] = node.detail
            return payload

        return sorted(
            (_node_json(node) for node in self.nodes),
            key=lambda item: (item["role"], item["block"] or "", item["line"]),
        )


def build_artifact_graph(input_path: Path, parser: NwchemParser) -> ArtifactGraph:
    """Build the cross-artifact graph from a parsed NWChem input.

    The model is generic: it records roles + the NWChem block that realizes
    each role + provenance. The same shape generalizes to other fleet backends
    because it never bakes in MatMaster/Bohrium runtime concepts (no image, no
    session, no submission policy).
    """
    graph = ArtifactGraph(input_path=input_path.resolve())
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_PRIMARY_INPUT,
            block=None,
            exists=True,
            source="case-root",
            line=1,
        )
    )
    for block_name, role in BLOCK_ROLE_BINDING.items():
        instances = parser.sections.get(block_name, [])
        if instances:
            for instance in instances:
                graph.nodes.append(
                    ArtifactNode(
                        role=role,
                        block=block_name,
                        exists=True,
                        source=f"nwchem block binding:{block_name}",
                        line=instance.start_line + 1,
                        detail={"end_line": (instance.end_line or 0) + 1},
                    )
                )
        else:
            graph.nodes.append(
                ArtifactNode(
                    role=role,
                    block=block_name,
                    exists=False,
                    source=f"nwchem block binding:{block_name}",
                    line=1,
                )
            )
    # ``task`` is a top-level directive, not a SECTION_KEYWORD, so the parser
    # does not fold it into ``sections``. Resolve it through the dedicated
    # task-directive scanner and record its line.
    task_lines = _task_directive_lines(parser)
    if task_lines:
        for line_no in task_lines:
            graph.nodes.append(
                ArtifactNode(
                    role=ROLE_TASK,
                    block="task",
                    exists=True,
                    source="nwchem directive binding:task",
                    line=line_no,
                )
            )
    else:
        graph.nodes.append(
            ArtifactNode(
                role=ROLE_TASK,
                block="task",
                exists=False,
                source="nwchem directive binding:task",
                line=1,
            )
        )
    # Top-level control directives (charge/memory/set) realize the control role
    # at the file scope rather than inside a block.
    control_line = _first_top_level_directive_line(parser, {"charge", "memory", "set"})
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_CONTROL,
            block=None,
            exists=control_line is not None,
            source="nwchem top-level directives: charge/memory/set",
            line=control_line or 1,
        )
    )
    return graph


# --- Preflight diagnostics -------------------------------------------------


def preflight_diagnostics(
    input_path: Path,
    *,
    intent: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], ArtifactGraph]:
    """Run universal generated-input preflight checks.

    Returns a tuple of (diagnostics, artifact_graph). Diagnostics are envelope
    dicts carrying the full ``DiagnosticEnvelope/v1`` field set so the agent
    CLI can emit them directly without re-shaping.
    """
    input_path = input_path.resolve()
    text = input_path.read_text(encoding="utf-8", errors="ignore")
    parser = NwchemParser(text)
    graph = build_artifact_graph(input_path, parser)

    version_assumption = resolve_version_assumption(intent)
    diagnostics: list[dict[str, Any]] = []
    diagnostics.extend(_missing_block_diagnostics(graph, parser))
    diagnostics.extend(_structure_diagnostics(parser, input_path))
    diagnostics.extend(_basis_diagnostics(parser, input_path))
    diagnostics.extend(_ecp_basis_diagnostics(parser, input_path))
    diagnostics.extend(_task_without_section_diagnostics(parser, input_path))
    diagnostics.extend(_low_memory_diagnostics(parser, input_path, intent))
    diagnostics.extend(_theory_basis_mismatch_diagnostics(parser, input_path, version_assumption))
    diagnostics.extend(_task_basis_mismatch_diagnostics(parser, input_path, version_assumption))
    diagnostics.extend(_dft_without_functional_diagnostics(parser, input_path, version_assumption))
    diagnostics.extend(_version_assumption_diagnostic(version_assumption, intent, input_path))

    return (
        sorted(
            diagnostics,
            key=lambda item: (
                item.get("range", {}).get("start", {}).get("line", 0),
                item.get("range", {}).get("start", {}).get("character", 0),
                item["code"],
            ),
        ),
        graph,
    )


def _diag(
    *,
    code: str,
    severity: str,
    message: str,
    path: Path,
    line: int = 1,
    column: int = 1,
    category: str,
    confidence: float,
    blocking: bool,
    source_provenance: dict[str, Any],
    fix_hints: list[str],
    actions: list[dict[str, Any]] | None = None,
    facts: dict[str, Any] | None = None,
    artifact_roles: list[str] | None = None,
    domain_tags: list[str] | None = None,
    version_assumption: dict[str, Any] | None = None,
    manual_ref: str | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single normalized preflight diagnostic.

    Carries every field the issue acceptance criteria require (``code``,
    ``severity``, ``path``/``range``, ``blocking``, ``category``,
    ``source_provenance``, ``fix_hints``/``actions``) plus the richer envelope
    fields (``facts``, ``artifact_roles``, ``domain_tags``,
    ``version_assumption``) used by the parent fleet probe.
    """
    line0 = max(line - 1, 0)
    col0 = max(column - 1, 0)
    payload: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
        "file": str(path),
        "path": str(path),
        "line": line,
        "column": column,
        "category": category,
        "confidence": confidence,
        "source": "nwchem-preflight",
        "range": {
            "start": {"line": line0, "character": col0},
            "end": {"line": line0, "character": col0 + 1},
        },
        "blocking": blocking,
        "fix_hints": fix_hints,
        "source_provenance": source_provenance,
    }
    if actions:
        payload["actions"] = actions
    if facts:
        payload["facts"] = facts
    if artifact_roles:
        payload["artifact_roles"] = artifact_roles
    if domain_tags:
        payload["domain_tags"] = domain_tags
    if version_assumption:
        payload["version_assumption"] = version_assumption
    if manual_ref:
        payload["manual_ref"] = manual_ref
    if intent:
        payload["intent"] = intent
    return payload


def _block_line(parser: NwchemParser, block_name: str) -> int:
    if block_name == "task":
        task_lines = _task_directive_lines(parser)
        return task_lines[0] if task_lines else 1
    instances = parser.sections.get(block_name, [])
    return (instances[0].start_line + 1) if instances else 1


def _missing_block_diagnostics(
    graph: ArtifactGraph, parser: NwchemParser
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # geometry is mandatory for any molecular calculation; task drives what
    # gets computed. Without either, NWChem has nothing runnable.
    for role, block_name in ((ROLE_STRUCTURE, "geometry"), (ROLE_TASK, "task")):
        node_iter = graph.by_role(role)
        node = next(iter(node_iter), None)
        if node is not None and not node.exists:
            out.append(
                _diag(
                    code=CODE_MISSING_BLOCK,
                    severity="error",
                    message=(
                        f"'{block_name}' is missing; NWChem requires it for "
                        f"the {role} artifact"
                    ),
                    path=graph.input_path,
                    line=1,
                    category="cross-file reference",
                    confidence=0.97,
                    blocking=True,
                    source_provenance={
                        "role": role,
                        "expected_block": block_name,
                        "present_blocks": sorted(parser.sections.keys()),
                    },
                    fix_hints=[
                        f"Add a '{block_name} ... end' block to the input",
                        "Or restore the block from the original template",
                    ],
                    actions=[
                        {
                            "kind": "insert_block",
                            "block": block_name,
                            "target": str(graph.input_path),
                            "safe_to_auto_apply": False,
                        }
                    ],
                    facts={
                        "missing_block": block_name,
                        "present_blocks": sorted(parser.sections.keys()),
                    },
                    artifact_roles=[role, ROLE_PRIMARY_INPUT],
                    domain_tags=["cross-block", "blocking"],
                )
            )
    return out


def _structure_diagnostics(parser: NwchemParser, path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    geom = parser.sections.get("geometry", [])
    if not geom:
        return out  # missing-block diagnostic already covers this.
    instance = geom[0]
    # A geometry block must declare at least one atom record after the
    # symmetry/title lines. An empty geometry is a silent runtime error.
    atom_count = _count_geometry_atoms(instance, parser)
    if atom_count == 0:
        out.append(
            _diag(
                code=CODE_STRUCTURE_EMPTY,
                severity="error",
                message="geometry block has no atom records; structure is empty",
                path=path,
                line=instance.start_line + 1,
                category="cross-file reference",
                confidence=0.9,
                blocking=True,
                source_provenance={
                    "role": ROLE_STRUCTURE,
                    "block": "geometry",
                    "atom_count": 0,
                },
                fix_hints=[
                    "Add atom records (<symbol> <x> <y> <z>) after the geometry header",
                    "Or import the geometry from an external coordinate source",
                ],
                actions=[
                    {
                        "kind": "insert_section",
                        "section": "atoms",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"atom_count": 0},
                artifact_roles=[ROLE_STRUCTURE],
                domain_tags=["cross-block", "blocking"],
            )
        )
    return out


def _ecp_basis_diagnostics(parser: NwchemParser, path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ecp = parser.sections.get("ecp", [])
    basis = parser.sections.get("basis", [])
    if not ecp:
        return out
    if not basis:
        return out  # missing-basis diagnostic already covers the absence.
    # An ECP must be paired with an all-electron-like basis choice; declaring
    # an ecp block while keeping a tiny minimal basis is a common silent
    # mistake.
    basis_library = _basis_library_name(basis[0], parser)
    if basis_library is not None and basis_library.lower() in _MINIMAL_BASIS_LIBRARY:
        out.append(
            _diag(
                code=CODE_ECP_WITHOUT_BASIS,
                severity="warning",
                message=(
                    f"ecp block declared but basis library '{basis_library}' is a "
                    "minimal set; pair the ECP with a correlation-consistent basis"
                ),
                path=path,
                line=basis[0].start_line + 1,
                category="semantic consistency",
                confidence=0.8,
                blocking=False,
                source_provenance={
                    "role": ROLE_PSEUDOPOTENTIAL,
                    "cross_referenced_role": ROLE_BASIS,
                    "basis_library": basis_library,
                },
                fix_hints=[
                    "Switch the basis library to a correlation-consistent family (cc-pvdz etc.)",
                    "Or remove the ecp block if a minimal basis is intentional",
                ],
                actions=[
                    {
                        "kind": "set_keyword",
                        "keyword": "library",
                        "value": "cc-pvdz",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"basis_library": basis_library, "ecp_present": True},
                artifact_roles=[ROLE_PSEUDOPOTENTIAL, ROLE_BASIS],
                domain_tags=["semantic", "non-blocking"],
            )
        )
    return out


def _basis_diagnostics(parser: NwchemParser, path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    basis = parser.sections.get("basis", [])
    if basis:
        return out  # a basis block is present; nothing missing.
    # Without a basis block NWChem falls back to a default basis, which is a
    # silent assumption the parent probe should be able to surface.
    out.append(
        _diag(
            code=CODE_MISSING_BASIS,
            severity="warning",
            message=(
                "no 'basis' block declared; NWChem will apply a default basis set"
            ),
            path=path,
            line=_block_line(parser, "task"),
            category="cross-file reference",
            confidence=0.85,
            blocking=False,
            source_provenance={
                "role": ROLE_BASIS,
                "task_present": bool(_task_directive_lines(parser)),
            },
            fix_hints=[
                "Add a 'basis ... end' block declaring library basis sets per element",
                "Or document the default basis assumption in the intent contract",
            ],
            actions=[
                {
                    "kind": "insert_block",
                    "block": "basis",
                    "target": str(path),
                    "safe_to_auto_apply": False,
                }
            ],
            facts={"basis_present": False},
            artifact_roles=[ROLE_BASIS, ROLE_TASK],
            domain_tags=["cross-block", "non-blocking"],
        )
    )
    return out


def _task_without_section_diagnostics(
    parser: NwchemParser, path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    task_lines = _task_directive_lines(parser)
    if not task_lines:
        return out  # missing-task-block diagnostic already covers the absence.
    # ``task <theory>`` must reference a theory section that was actually
    # declared (e.g. ``task dft`` requires a ``dft`` block). A task pointing
    # at an undeclared section is a classic NWChem startup failure.
    for line_no in task_lines:
        theory = _task_theory_at_line(parser, line_no)
        if theory is None:
            continue
        section_blocks = parser.sections.get(theory, [])
        # DFT/CCSD/CCSD(T) require their own block to configure the driver and
        # options before they can run. SCF and MP2 can run from defaults off
        # the SCF wavefunction, so they are intentionally excluded here.
        if not section_blocks and theory in {"dft", "ccsd", "ccsd(t)"}:
            out.append(
                _diag(
                    code=CODE_TASK_WITHOUT_SECTION,
                    severity="error",
                    message=(
                        f"task directive targets '{theory}' but no '{theory}' "
                        f"block was declared"
                    ),
                    path=path,
                    line=line_no,
                    category="semantic consistency",
                    confidence=0.92,
                    blocking=True,
                    source_provenance={
                        "role": ROLE_TASK,
                        "cross_referenced_role": _theory_role(theory),
                        "task_theory": theory,
                        "theory_section_present": False,
                    },
                    fix_hints=[
                        f"Add a '{theory} ... end' block before the task directive",
                        "Or change the task theory to one with an existing section",
                    ],
                    actions=[
                        {
                            "kind": "insert_block",
                            "block": theory,
                            "target": str(path),
                            "safe_to_auto_apply": False,
                        }
                    ],
                    facts={"task_theory": theory, "theory_section_present": False},
                    artifact_roles=[ROLE_TASK, _theory_role(theory)],
                    domain_tags=["cross-block", "blocking"],
                )
            )
    return out


def _low_memory_diagnostics(
    parser: NwchemParser, path: Path, intent: dict[str, Any] | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    memory_mb, memory_line = _memory_directive(parser)
    if memory_mb is None:
        return out
    threshold = float(
        (intent or {}).get("memory_warning_mb", DEFAULT_MEMORY_WARNING_MB)
    )
    if memory_mb < threshold:
        out.append(
            _diag(
                code=CODE_LOW_MEMORY,
                severity="warning",
                message=(
                    f"memory {memory_mb:g} mb is below the conservative workflow "
                    f"threshold ({threshold:g} mb); large basis/MP2/CC runs may stall"
                ),
                path=path,
                line=memory_line,
                category="preflight/runtime-risk",
                confidence=0.75,
                blocking=False,
                source_provenance={
                    "role": ROLE_PRIMARY_INPUT,
                    "directive": "memory",
                    "threshold_source": (
                        "intent" if "memory_warning_mb" in (intent or {}) else "default"
                    ),
                },
                fix_hints=[
                    f"Raise memory to at least {threshold:g} mb",
                    "Or document the smaller allocation in the intent contract",
                ],
                actions=[
                    {
                        "kind": "set_directive",
                        "directive": "memory",
                        "value": f"{threshold:g} mb",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"memory_mb": memory_mb, "threshold": threshold},
                artifact_roles=[ROLE_PRIMARY_INPUT, ROLE_CONTROL],
                domain_tags=["preflight", "runtime-risk"],
            )
        )
    return out


def _theory_basis_mismatch_diagnostics(
    parser: NwchemParser, path: Path, version_assumption: dict[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    task_lines = _task_directive_lines(parser)
    basis = parser.sections.get("basis", [])
    if not task_lines or not basis:
        return out
    correlated_theory = None
    for line_no in task_lines:
        theory = _task_theory_at_line(parser, line_no)
        if theory and theory in _CORRELATED_THEORIES:
            correlated_theory = theory
            break
    if correlated_theory is None:
        return out
    basis_library = _basis_library_name(basis[0], parser)
    if basis_library is None:
        return out
    # Correlated methods (MP2/CCSD) on a minimal basis produce noise; surface
    # this as a version/method compatibility finding the parent probe can act on.
    if basis_library.lower() in _MINIMAL_BASIS_LIBRARY:
        out.append(
            _diag(
                code=CODE_THEORY_BASIS_MISMATCH,
                severity="error",
                message=(
                    f"Correlated task theory '{correlated_theory}' is not meaningful "
                    f"with the minimal basis library '{basis_library}'"
                ),
                path=path,
                line=basis[0].start_line + 1,
                category="schema",
                confidence=0.9,
                blocking=True,
                source_provenance={
                    "role": ROLE_BASIS,
                    "task_theory": correlated_theory,
                    "basis_library": basis_library,
                    "schema_source": "nwchem-lsp builtin theory/basis matrix",
                },
                fix_hints=[
                    f"Switch the basis library to a polarized family for {correlated_theory}",
                    "Or downgrade to a single-point SCF task",
                ],
                actions=[
                    {
                        "kind": "set_keyword",
                        "keyword": "library",
                        "value": "cc-pvdz",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"task_theory": correlated_theory, "basis_library": basis_library},
                artifact_roles=[ROLE_BASIS, ROLE_TASK],
                domain_tags=["schema", "version-aware", "blocking"],
                version_assumption=version_assumption,
            )
        )
    return out


def _task_basis_mismatch_diagnostics(
    parser: NwchemParser, path: Path, version_assumption: dict[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # task dft should pair with a basis that supports DFT (most do, but the
    # absence of any basis block on a DFT task is a stronger warning than the
    # generic missing-basis note). This check is informational and only fires
    # when a task dft exists with no basis block at all and no library default.
    task_lines = _task_directive_lines(parser)
    basis = parser.sections.get("basis", [])
    if not task_lines or basis:
        return out
    has_dft_task = any(
        (_task_theory_at_line(parser, line_no) == "dft") for line_no in task_lines
    )
    if not has_dft_task:
        return out
    out.append(
        _diag(
            code=CODE_TASK_BASIS_MISMATCH,
            severity="warning",
            message=(
                "task dft has no 'basis' block; NWChem will pick an implicit "
                "default that may not match the intended functional"
            ),
            path=path,
            line=task_lines[0],
            category="schema",
            confidence=0.78,
            blocking=False,
            source_provenance={
                "role": ROLE_DFT,
                "cross_referenced_role": ROLE_BASIS,
                "task_theory": "dft",
                "basis_present": False,
                "schema_source": "nwchem-lsp builtin task/basis matrix",
            },
            fix_hints=[
                "Add a 'basis ... end' block with a library suitable for DFT",
                "Or document the implicit default in the intent contract",
            ],
            actions=[
                {
                    "kind": "insert_block",
                    "block": "basis",
                    "target": str(path),
                    "safe_to_auto_apply": False,
                }
            ],
            facts={"task_theory": "dft", "basis_present": False},
            artifact_roles=[ROLE_DFT, ROLE_BASIS, ROLE_TASK],
            domain_tags=["schema", "version-aware", "non-blocking"],
            version_assumption=version_assumption,
        )
    )
    return out


def _dft_without_functional_diagnostics(
    parser: NwchemParser, path: Path, version_assumption: dict[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    dft = parser.sections.get("dft", [])
    if not dft:
        return out
    instance = dft[0]
    # A dft block should declare an XC functional (``xc ...``). Without one
    # NWChem falls back to a default functional, which is a silent assumption.
    xc_line, _xc_value = _dft_xc(instance, parser)
    if xc_line is None:
        out.append(
            _diag(
                code=CODE_DFT_WITHOUT_FUNCTIONAL,
                severity="warning",
                message=(
                    "dft block declares no 'xc' functional; NWChem will use a "
                    "default functional"
                ),
                path=path,
                line=instance.start_line + 1,
                category="schema",
                confidence=0.82,
                blocking=False,
                source_provenance={
                    "role": ROLE_DFT,
                    "keyword": "xc",
                    "schema_source": "nwchem-lsp builtin keyword schema",
                },
                fix_hints=[
                    "Add an 'xc <functional>' line to the dft block (e.g. xc b3lyp)",
                    "Or document the default functional in the intent contract",
                ],
                actions=[
                    {
                        "kind": "set_keyword",
                        "keyword": "xc",
                        "value": "b3lyp",
                        "target": str(path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"xc_present": False},
                artifact_roles=[ROLE_DFT],
                domain_tags=["schema", "version-aware", "non-blocking"],
                version_assumption=version_assumption,
            )
        )
    return out


# --- version-aware-keywords ------------------------------------------------


def resolve_version_assumption(intent: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve the explicit runtime/version assumption for this preflight run.

    When the exact runtime/image version is unknown we record that fact
    explicitly rather than guessing, per the issue's version-assumptions
    acceptance criterion. The intent contract can override ``software_version``
    (e.g. ``nwchem >=7.2``); otherwise we fall back to the schema version the
    builtin keyword set was authored against.
    """
    intent = intent or {}
    software_version = intent.get("software_version")
    runtime_image = intent.get("runtime_image")
    assumption: dict[str, Any] = {
        "software": "nwchem",
        "software_version": software_version or "unknown",
        "runtime_image": runtime_image or "unknown",
        "schema_source": intent.get("schema_source", "nwchem-lsp builtin"),
        # The fallback is intentional and explicit so consumers never have to
        # guess whether ``unknown`` means "not checked" or "could not determine".
        "exact_runtime_known": bool(software_version or runtime_image),
    }
    if software_version or runtime_image:
        assumption["declared_by"] = "intent"
    else:
        assumption["declared_by"] = "fallback"
    return assumption


def _version_assumption_diagnostic(
    version_assumption: dict[str, Any],
    intent: dict[str, Any] | None,
    path: Path,
) -> list[dict[str, Any]]:
    """Emit an explicit information diagnostic when the runtime version is unknown.

    This makes the version assumption machine-readable in the diagnostic stream
    itself (not just metadata) so the parent probe can surface it without
    parsing the envelope top-level.
    """
    if version_assumption["exact_runtime_known"]:
        return []
    return [
        _diag(
            code=CODE_VERSION_ASSUMPTION,
            severity="information",
            message=(
                "Exact NWChem runtime/image version is unknown; preflight "
                "validated against the builtin keyword set"
            ),
            path=path,
            line=1,
            category="preflight/runtime-risk",
            confidence=1.0,
            blocking=False,
            source_provenance={
                "role": ROLE_PRIMARY_INPUT,
                "reason": "software_version and runtime_image not declared in intent",
            },
            fix_hints=[
                "Declare software_version/runtime_image in the intent contract",
            ],
            actions=[],
            facts={
                "software_version": version_assumption["software_version"],
                "runtime_image": version_assumption["runtime_image"],
                "schema_source": version_assumption["schema_source"],
            },
            artifact_roles=[ROLE_PRIMARY_INPUT],
            domain_tags=["version-aware", "assumption"],
            version_assumption=version_assumption,
            intent=dict(intent) if intent else None,
        )
    ]


# --- fleet-regression-fixtures --------------------------------------------


def fleet_manifest(
    *,
    fixtures: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a machine-readable preflight manifest for the parent fleet.

    The parent ``bohrium_skills`` probe/report workflow consumes this to know
    which preflight codes exist, which capabilities are implemented, and which
    fixtures exercise them. Keeping it as data (not README prose) means the
    fleet regression evidence stays in sync with the implementation.
    """
    codes = {
        CODE_MISSING_BLOCK: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "mandatory geometry/task block absent from input",
        },
        CODE_STRUCTURE_EMPTY: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "geometry block has no atom records",
        },
        CODE_MISSING_BASIS: {
            "severity": "warning",
            "category": "cross-file reference",
            "blocking": False,
            "capability": "cross-artifact-graph",
            "summary": "no basis block declared; default basis assumed",
        },
        CODE_ECP_WITHOUT_BASIS: {
            "severity": "warning",
            "category": "semantic consistency",
            "blocking": False,
            "capability": "cross-artifact-graph",
            "summary": "ecp block paired with a minimal basis library",
        },
        CODE_TASK_WITHOUT_SECTION: {
            "severity": "error",
            "category": "semantic consistency",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "task targets a theory with no matching section",
        },
        CODE_LOW_MEMORY: {
            "severity": "warning",
            "category": "preflight/runtime-risk",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "memory directive below conservative threshold",
        },
        CODE_THEORY_BASIS_MISMATCH: {
            "severity": "error",
            "category": "schema",
            "blocking": True,
            "capability": "version-aware-keywords",
            "summary": "correlated task theory on a minimal basis",
        },
        CODE_TASK_BASIS_MISMATCH: {
            "severity": "warning",
            "category": "schema",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "task dft without any basis block",
        },
        CODE_DFT_WITHOUT_FUNCTIONAL: {
            "severity": "warning",
            "category": "schema",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "dft block declares no xc functional",
        },
        CODE_VERSION_ASSUMPTION: {
            "severity": "information",
            "category": "preflight/runtime-risk",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "exact runtime version unknown; fallback schema used",
        },
    }
    capabilities = {
        "version-aware-keywords": {
            "status": "available",
            "evidence_codes": [
                CODE_THEORY_BASIS_MISMATCH,
                CODE_TASK_BASIS_MISMATCH,
                CODE_DFT_WITHOUT_FUNCTIONAL,
                CODE_LOW_MEMORY,
                CODE_VERSION_ASSUMPTION,
            ],
        },
        "cross-artifact-graph": {
            "status": "available",
            "roles": list(ALL_ROLES),
            "evidence_codes": [
                CODE_MISSING_BLOCK,
                CODE_STRUCTURE_EMPTY,
                CODE_MISSING_BASIS,
                CODE_ECP_WITHOUT_BASIS,
                CODE_TASK_WITHOUT_SECTION,
            ],
        },
        "code-actions": {
            "status": "available",
            "blocking_gate": "nwchem-lsp-tool check --fail-on-blocking",
            "evidence_codes": list(codes.keys()),
        },
        "fleet-regression-fixtures": {
            "status": "available",
            "fixtures": list(fixtures) if fixtures else [],
        },
    }
    return {
        "software": "nwchem",
        "preflight_envelope": "DiagnosticEnvelope/v1",
        "artifact_roles": list(ALL_ROLES),
        "capabilities": capabilities,
        "codes": codes,
    }


# --- helpers ---------------------------------------------------------------


def _theory_role(theory: str) -> str:
    """Map a NWChem theory name to its generic artifact role."""
    if theory == "dft":
        return ROLE_DFT
    if theory == "scf":
        return ROLE_SCF_CONTROL
    return ROLE_TASK


def _count_geometry_atoms(instance: NWchemSection, parser: NwchemParser) -> int:
    """Count atom records inside a geometry block.

    A geometry record looks like ``<Symbol> <x> <y> <z>`` (optionally with a
    leading index or trailing charge). Lines starting with a known directive
    (``geometry``, ``symmetry``, ``noautoz``, ``units``, comments) are skipped.
    """
    directives = {
        "geometry",
        "symmetry",
        "noautosym",
        "autosym",
        "noautoz",
        "autoz",
        "units",
        "bq",
    }
    count = 0
    end_line = instance.end_line if instance.end_line is not None else len(parser.lines) - 1
    for index in range(instance.start_line + 1, end_line + 1):
        if index >= len(parser.lines):
            break
        stripped = parser.lines[index].strip().lower()
        if not stripped or stripped.startswith("#") or stripped == "end":
            continue
        parts = stripped.split()
        first = parts[0]
        if first in directives:
            continue
        # Atom records carry a leading element symbol followed by 3+ numbers.
        if len(parts) >= 4 and _looks_like_atom_record(parts):
            count += 1
    return count


def _looks_like_atom_record(parts: list[str]) -> bool:
    """Heuristic: <Symbol|index> <x> <y> <z>."""
    # Skip the first token (element symbol or numeric index); the next three
    # must parse as floats.
    coords = parts[1:4] if _is_symbol(parts[0]) else parts[:3]
    if len(coords) < 3:
        return False
    try:
        for token in coords[:3]:
            float(token)
    except ValueError:
        return False
    return True


def _is_symbol(token: str) -> bool:
    return bool(token) and token[0].isalpha()


def _basis_library_name(instance: NWchemSection, parser: NwchemParser) -> str | None:
    """Return the first ``library`` basis-set name inside a basis block.

    NWChem basis blocks name a library basis per element with either
    ``library <element> <name>`` or ``<element> library <name>``; we accept both
    orderings so the preflight matches the dialect actually used by templates.
    """
    end_line = instance.end_line if instance.end_line is not None else len(parser.lines) - 1
    for index in range(instance.start_line + 1, end_line + 1):
        if index >= len(parser.lines):
            break
        stripped = parser.lines[index].strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        # ``library <element> <name>``
        if len(parts) >= 3 and parts[0] == "library":
            return parts[2]
        # ``<element> library <name>``
        if len(parts) >= 3 and parts[1] == "library":
            return parts[2]
    return None


def _task_theory_at_line(parser: NwchemParser, line_no: int) -> str | None:
    """Return the theory named by a ``task <theory>`` directive at 1-based line."""
    index = line_no - 1
    if index < 0 or index >= len(parser.lines):
        return None
    line = parser.lines[index].strip().lower()
    parts = line.split()
    if len(parts) >= 2 and parts[0] == "task":
        return parts[1]
    return None


def _task_directive_lines(parser: NwchemParser) -> list[int]:
    """Return 1-based line numbers of every top-level ``task`` directive."""
    lines: list[int] = []
    for index, raw in enumerate(parser.lines):
        stripped = raw.strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if parts and parts[0] == "task" and len(parts) >= 2:
            lines.append(index + 1)
    return lines


def _memory_directive(parser: NwchemParser) -> tuple[float | None, int]:
    """Parse the top-level ``memory`` directive into (megabytes, line)."""
    for index, raw in enumerate(parser.lines):
        stripped = raw.strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if not parts or parts[0] != "memory":
            continue
        mb = _parse_memory_mb(parts[1:])
        if mb is None:
            continue
        return mb, index + 1
    return None, 1


def _parse_memory_mb(tokens: list[str]) -> float | None:
    """Parse a memory magnitude like ``1200 mb`` / ``2 gb`` into megabytes."""
    if not tokens:
        return None
    magnitude_token = tokens[0]
    unit_token = tokens[1] if len(tokens) > 1 else ""
    try:
        magnitude = float(magnitude_token)
    except ValueError:
        return None
    unit = unit_token.lower() if unit_token else "mb"
    factors = {"b": 1e-6, "kb": 1e-3, "mb": 1.0, "gb": 1e3, "tb": 1e6}
    factor = factors.get(unit)
    if factor is None:
        return None
    return magnitude * factor


def _dft_xc(instance: NWchemSection, parser: NwchemParser) -> tuple[int | None, str | None]:
    """Return (line_number, value) for the first ``xc`` directive in a dft block."""
    end_line = instance.end_line if instance.end_line is not None else len(parser.lines) - 1
    for index in range(instance.start_line + 1, end_line + 1):
        if index >= len(parser.lines):
            break
        stripped = parser.lines[index].strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if parts and parts[0] == "xc":
            value = stripped[len(parts[0]):].strip() if len(parts) > 1 else ""
            return index + 1, value
    return None, None


def _first_top_level_directive_line(
    parser: NwchemParser, names: set[str]
) -> int | None:
    """Return the 1-based line of the first top-level directive in ``names``.

    A top-level directive appears outside any block; the NWChem parser already
    folds ``task`` into a synthetic section, so we only need to scan lines that
    start with one of ``names`` and are not inside a block section.
    """
    in_block = False
    for index, raw in enumerate(parser.lines):
        stripped = raw.strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        first = parts[0]
        if first in NwchemParser.SECTION_KEYWORDS:
            in_block = True
            continue
        if first == "end":
            in_block = False
            continue
        if in_block:
            continue
        if first in names:
            return index + 1
    return None


# Used by the tool layer to detect NWChem input without parsing the whole file,
# so a single-line probe stays cheap.
_NWCHEM_BLOCK_RE = re.compile(
    r"^\s*(geometry|basis|ecp|scf|dft|task)\b", re.IGNORECASE | re.MULTILINE
)


def looks_like_nwchem_workspace(path: Path) -> bool:
    """True when a path is a real NWChem generated-input artifact.

    Preflight accepts either an ``.nw``/``.nwinp`` file or a directory
    containing one; a directory with no NWChem input falls back to the legacy
    single-file lint path so callers that progressively build inputs are not
    flooded with blocking missing-block errors before the input exists.
    """
    if path.is_file():
        return path.suffix.lower() in {".nw", ".nwinp"} or _has_nwchem_block(path)
    if not path.is_dir():
        return False
    return any(_has_nwchem_entry(child) for child in path.iterdir())


def _has_nwchem_entry(child: Path) -> bool:
    if not child.is_file():
        return False
    return child.suffix.lower() in {".nw", ".nwinp"} or _has_nwchem_block(child)


def _has_nwchem_block(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return bool(_NWCHEM_BLOCK_RE.search(text)) and (
        bool(re.search(r"^\s*end\b", text, re.IGNORECASE | re.MULTILINE))
        or bool(re.search(r"^\s*task\b", text, re.IGNORECASE | re.MULTILINE))
    )

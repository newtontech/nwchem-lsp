#!/usr/bin/env bash
set -euo pipefail

wheel="${1:?wheel path is required}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv="$(mktemp -d)"
trap 'rm -rf "$venv"' EXIT

python3 -m venv "$venv"
"$venv/bin/python" -m pip install --quiet "$wheel"
"$venv/bin/nwchem-lsp" --help
"$venv/bin/nwchem-lsp" --version
"$venv/bin/nwchem-lsp-tool" --help
"$venv/bin/nwchem-lsp-tool" capabilities --format json
"$venv/bin/nwchem-lsp-tool" check "$root/tests/fixtures/valid/water_scf.nw" --format json
"$venv/bin/nwchem-lsp-tool" check "$root/tests/fixtures/invalid/missing_required.nw" --format json
"$venv/bin/nwchem-lsp-tool" logs "$root/tests/fixtures/logs/scf_not_converged.out" --format json

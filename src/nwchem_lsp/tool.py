"""Agent-facing CLI for Diagnostic Engine v1 operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lsprotocol.types import Position

from .features.completion import NwchemCompletionProvider
from .features.diagnostic import NwchemDiagnosticProvider
from .features.hover import NwchemHoverProvider
from .features.symbols import NwchemSymbolProvider
from .server import NWChemLanguageServer
from .skill_export import SKILL_SPEC, export_skill, skill_spec_text

SOFTWARE = "nwchem"


def _file_type(path: Path) -> str:
    if "." in path.name:
        return path.suffix.lstrip(".").lower()
    return path.name.lower()


def _server() -> NWChemLanguageServer:
    return NWChemLanguageServer()


def _diagnostics(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    provider = NwchemDiagnosticProvider(_server())
    return [provider.to_envelope(diag).to_dict() for diag in provider.get_diagnostics(text)]


def _summary(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    blocking = [item for item in diagnostics if item.get("blocking")]
    return {
        "diagnostics": len(diagnostics),
        "blocking": len(blocking),
        "readiness": "blocked" if blocking else "ready",
        "reason": (
            "blocking diagnostics remain"
            if blocking
            else "no blocking diagnostics were reported"
        ),
    }


def check_path(path: Path) -> dict[str, Any]:
    diagnostics = _diagnostics(path)
    summary = _summary(diagnostics)
    return {
        "schema": "DiagnosticEnvelope/v1",
        "software": SOFTWARE,
        "operation": "check",
        "ok": not bool(summary["blocking"]),
        "path": str(path),
        "uri": path.resolve().as_uri(),
        "file_type": _file_type(path),
        "diagnostics": diagnostics,
        "summary": summary,
        "tool_available": True,
        "files_checked": [str(path)],
    }


def _capabilities_payload() -> dict[str, Any]:
    return {
        "schema": "OpenQCLspCapabilities",
        "version": 1,
        "id": SKILL_SPEC["package"]["name"],
        "software": SKILL_SPEC["software"],
        "displayName": SKILL_SPEC["display_name"],
        "executable": SKILL_SPEC["entrypoints"]["server"],
        "filePatterns": SKILL_SPEC["file_patterns"],
        "capabilities": [
            "diagnostics",
            "rich-diagnostics",
            "completion",
            "hover",
            "symbols",
            "fix-preview",
            "pluggable-skill",
        ],
        "agentCli": {
            "command": SKILL_SPEC["entrypoints"]["tool"],
            "operations": SKILL_SPEC["operations"],
            "jsonFormat": True,
            "failOnBlocking": True,
        },
        "diagnosticContract": SKILL_SPEC["diagnostic_contract"],
    }


def _position(line: int, character: int) -> Position:
    return Position(line=line, character=character)


def _completion_item_to_dict(item: Any) -> dict[str, Any]:
    return {
        "label": getattr(item, "label", None),
        "kind": int(getattr(item, "kind", 0) or 0),
        "detail": getattr(item, "detail", None),
        "documentation": getattr(item, "documentation", None),
    }


def _hover_to_dict(hover: Any) -> dict[str, Any]:
    if hover is None:
        return {"contents": None}
    contents = getattr(hover, "contents", None)
    return {
        "contents": getattr(contents, "value", contents),
        "kind": getattr(contents, "kind", None),
    }


def _symbol_to_dict(symbol: Any) -> dict[str, Any]:
    return {
        "name": getattr(symbol, "name", None),
        "kind": int(getattr(symbol, "kind", 0) or 0),
        "detail": getattr(symbol, "detail", None),
        "range": {
            "start": {
                "line": symbol.range.start.line,
                "character": symbol.range.start.character,
            },
            "end": {
                "line": symbol.range.end.line,
                "character": symbol.range.end.character,
            },
        },
    }


def _operation_payload(path: Path, operation: str, line: int, character: int) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    server = _server()
    position = _position(line, character)
    if operation == "complete":
        items = NwchemCompletionProvider(server).get_completions(text, position)
        return {
            "software": SOFTWARE,
            "operation": operation,
            "path": str(path),
            "items": [_completion_item_to_dict(item) for item in items],
        }
    if operation == "hover":
        hover = NwchemHoverProvider(server).get_hover(text, position)
        return {
            "software": SOFTWARE,
            "operation": operation,
            "path": str(path),
            "hover": _hover_to_dict(hover),
        }
    if operation == "symbols":
        symbols = NwchemSymbolProvider(server).get_document_symbols(text)
        return {
            "software": SOFTWARE,
            "operation": operation,
            "path": str(path),
            "symbols": [_symbol_to_dict(symbol) for symbol in symbols],
        }
    if operation == "fix":
        return {
            "software": SOFTWARE,
            "operation": operation,
            "path": str(path),
            "fixes": [
                item["fix_preview"]
                for item in _diagnostics(path)
                if item.get("fix_preview") is not None
            ],
            "advisory": True,
        }
    return {
        "software": SOFTWARE,
        "operation": operation,
        "path": str(path),
        "diagnostics": _diagnostics(path),
        "summary": _summary(_diagnostics(path)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nwchem-lsp-tool")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    capabilities = subparsers.add_parser("capabilities")
    capabilities.add_argument("--format", choices=["json"], default="json")
    skill_spec = subparsers.add_parser("skill-spec")
    skill_spec.add_argument("--format", choices=["json", "yaml"], default="json")
    skill_export = subparsers.add_parser("skill-export")
    skill_export.add_argument("--output", type=Path, required=True)
    for operation in ("check", "context", "complete", "hover", "symbols", "fix"):
        sub = subparsers.add_parser(operation)
        sub.add_argument("path", type=Path)
        sub.add_argument("--format", choices=["json"], default="json")
        sub.add_argument("--line", type=int, default=0)
        sub.add_argument("--character", type=int, default=0)
        if operation == "check":
            sub.add_argument("--fail-on-blocking", action="store_true")
    args = parser.parse_args(argv)
    if args.operation == "capabilities":
        print(json.dumps(_capabilities_payload(), indent=2, sort_keys=True))
        return 0
    if args.operation == "skill-spec":
        print(skill_spec_text(args.format))
        return 0
    if args.operation == "skill-export":
        print(json.dumps(export_skill(args.output), indent=2, sort_keys=True))
        return 0
    if args.operation == "check":
        payload = check_path(args.path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if getattr(args, "fail_on_blocking", False) and not payload["ok"] else 0
    payload = _operation_payload(args.path, args.operation, args.line, args.character)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate the family-wide F1 help reference (GATE-HELPREF).

Every Quill app answers F1 with an authored window purpose and per-control
help. That content lives where it runs -- ``surface_help`` catalogues and
inline ``SetHelpText`` calls -- and this tool renders all of it into one
reviewable, searchable document: ``docs/f1-help-reference.md``. Like the
keyboard reference and ``CONTROL_REFERENCE.md`` (the QUILL editor's own
F1 topics), it is generated, so it cannot drift from what the apps
actually say: the drift gate (``tests/unit/tools/test_help_reference.py``)
fails when the catalogues or the authored help change without a rebuild.

Per app it documents:

* every window title and its authored purpose (exact and prefix entries);
* every authored control help sentence, grouped by module and window
  class, with the control expression it is attached to;
* the audit's coverage counts, straight from the committed inventory.

Regenerate::

    python -m quill.tools.build_help_reference --write
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_PATH = _REPO_ROOT / "docs" / "f1-help-reference.md"


@dataclass(frozen=True)
class AppConfig:
    display: str
    catalogue_module: str
    scan_dirs: tuple[str, ...]
    scan_globs: tuple[str, ...]
    inventory: str  # fixture filename, "" when the app predates the audits


APPS: tuple[AppConfig, ...] = (
    AppConfig(
        "Quill Radio",
        "quill.core.radio.surface_help",
        ("quill/ui/radio",),
        ("quill/apps/radio*.py",),
        "radio_help_inventory.json",
    ),
    AppConfig(
        "QUILL Cast",
        "quill.core.podcasts.surface_help",
        ("quill/ui/podcasts",),
        ("quill/apps/podcasts*.py",),
        "cast_help_inventory.json",
    ),
    AppConfig(
        "QUILL Media Player",
        "quill.core.media.surface_help",
        ("quill/ui/media",),
        ("quill/apps/player.py",),
        "player_help_inventory.json",
    ),
    AppConfig(
        "QUILL Audio Studio",
        "quill.core.audio_studio.surface_help",
        ("quill/ui/audio_studio",),
        ("quill/apps/studio.py",),
        "studio_help_inventory.json",
    ),
    AppConfig(
        "Quill Inkwell",
        "quill.core.inkwell_surface_help",
        (),
        ("quill/apps/inkwell.py",),
        "inkwell_help_inventory.json",
    ),
    AppConfig(
        "Quill Weather",
        "quill.core.weather.surface_help",
        ("quill/ui/weather",),
        ("quill/apps/weather.py",),
        "weather_help_inventory.json",
    ),
    AppConfig(
        "Quill Converter",
        "quill.core.converter_surface_help",
        (),
        ("quill/apps/converter.py",),
        "converter_help_inventory.json",
    ),
    AppConfig(
        "Quill Beacon",
        "quill.apps.beacon.surface_help",
        ("quill/apps/beacon",),
        (),
        "beacon_help_inventory.json",
    ),
)

_FIXTURES = _REPO_ROOT / "tests" / "unit" / "ui" / "fixtures"


def _scan_paths(config: AppConfig) -> list[Path]:
    paths: list[Path] = []
    for rel in config.scan_dirs:
        paths.extend(sorted((_REPO_ROOT / rel).glob("*.py")))
    for pattern in config.scan_globs:
        paths.extend(sorted(_REPO_ROOT.glob(pattern)))
    return paths


def _authored_help(path: Path) -> list[tuple[str, str, str]]:
    """``(window_class, control_expr, help_text)`` per SetHelpText literal."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    out: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "SetHelpText"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            continue
        receiver = ast.unparse(node.func.value)
        scope: ast.AST | None = node
        window = ""
        while scope is not None:
            if isinstance(scope, ast.ClassDef):
                window = scope.name
                break
            scope = parents.get(scope)
        out.append((window or "(module level)", receiver, node.args[0].value))
    return out


def _catalogue(config: AppConfig) -> tuple[dict[str, str], dict[str, str]]:
    module = importlib.import_module(config.catalogue_module)
    purposes = dict(getattr(module, "PURPOSES", {}))
    prefixes = dict(getattr(module, "PREFIX_PURPOSES", {}))
    return purposes, prefixes


def _inventory_counts(config: AppConfig) -> dict[str, int]:
    path = _FIXTURES / config.inventory
    if not config.inventory or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for status in data.values():
        counts[status] = counts.get(status, 0) + 1
    return counts


def generate() -> str:
    lines: list[str] = [
        "<!-- AUTO-GENERATED FILE. Do not hand-edit.",
        "    Generated by quill/tools/build_help_reference.py from each app's",
        "    surface_help catalogue and inline SetHelpText calls.",
        "    To update: python -m quill.tools.build_help_reference --write -->",
        "",
        "# The Quill family F1 help reference",
        "",
        "Press F1 anywhere, in any Quill app, and a help window opens with two",
        "answers: what the window you are in is *for*, and what the control",
        "under focus wants. This document is the complete authored content of",
        "that experience -- every window purpose and every control help",
        "sentence, per app -- generated from the same catalogues and",
        "`SetHelpText` calls the apps read at runtime, so it cannot drift.",
        "",
        "Controls without an authored sentence still answer F1: the engine",
        "composes their accessible name (in this family, usually a teaching",
        "sentence of its own) with a how-to-drive-it line for the control's",
        "kind. Coverage is enforced per app by the help-audit gates; the",
        "counts below come from the committed inventories.",
        "",
        "The QUILL editor's own F1 topics (492 of them) are documented",
        "separately in [CONTROL_REFERENCE.md](CONTROL_REFERENCE.md), generated",
        "from `topics.json` by `quill/tools/build_docs.py`.",
        "",
    ]
    for config in APPS:
        try:
            purposes, prefixes = _catalogue(config)
        except (ImportError, AttributeError):
            continue
        lines.append(f"## {config.display}")
        lines.append("")
        counts = _inventory_counts(config)
        if counts:
            total = sum(counts.values())
            parts = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
            lines.append(f"Control coverage: {total} audited sites ({parts}).")
            lines.append("")
        lines.append("### Every window, and what it is for")
        lines.append("")
        for title in sorted(purposes):
            lines.append(f"**{title}.** {purposes[title]}")
            lines.append("")
        for prefix in sorted(prefixes):
            lines.append(f'**Windows titled "{prefix}...".** {prefixes[prefix]}')
            lines.append("")
        authored: list[tuple[str, str, str, str]] = []
        for path in _scan_paths(config):
            rel = path.relative_to(_REPO_ROOT).as_posix()
            for window, receiver, text in _authored_help(path):
                authored.append((rel, window, receiver, text))
        if authored:
            lines.append("### Every authored control help sentence")
            lines.append("")
            current = ""
            for rel, window, receiver, text in authored:
                heading = f"{rel} -- {window}"
                if heading != current:
                    current = heading
                    lines.append(f"#### {window} (`{rel}`)")
                    lines.append("")
                lines.append(f"- `{receiver}`: {text}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    fresh = generate()
    if args.write:
        OUTPUT_PATH.write_text(fresh, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT_PATH.relative_to(_REPO_ROOT)}")
        return 0
    committed = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if committed != fresh:
        print(
            "docs/f1-help-reference.md has drifted. Regenerate with: "
            "python -m quill.tools.build_help_reference --write"
        )
        return 1
    print("f1-help-reference.md matches the authored help.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

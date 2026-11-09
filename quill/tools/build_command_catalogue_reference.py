"""Generate "What you can say in each app" from the catalogue (GATE-CATREF).

``docs/command-catalogue.md`` lists, for every catalogued app, each command a
sentence can reach: its name, its key, what it does, and the ways a person
might ask for it. It is generated from :mod:`quill.core.command_catalogue`, so
it cannot drift from what the Command Key actually understands; the drift gate
is ``tests/unit/tools/test_command_catalogue_reference.py``.

    python -m quill.tools.build_command_catalogue_reference --write
    python -m quill.tools.build_command_catalogue_reference --check
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from quill.core.command_catalogue import CommandSpec, Risk, rows_for_app

_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = _ROOT / "docs" / "command-catalogue.md"

_APP_NAMES = {"quill": "QUILL", "lite": "QUILL Lite", "radio": "Quill Radio"}


def _quill_key(command_id: str) -> str:
    from quill.core.keymap import DEFAULT_KEYMAP

    return DEFAULT_KEYMAP.get(command_id, "")


def _lite_key(command_id: str) -> str:
    from quill.core.lite.commands import COMMANDS

    handler = command_id.removeprefix("lite.")
    for _menu, _label, key, row_handler, _kind in COMMANDS:
        if row_handler == handler:
            return str(key or "")
    return ""


def _radio_key(command_id: str) -> str:
    from quill.core.app_keymaps import APP_KEYMAPS

    return APP_KEYMAPS["radio"].get(command_id, "")


_KEYS: dict[str, Callable[[str], str]] = {
    "quill": _quill_key,
    "lite": _lite_key,
    "radio": _radio_key,
}


def _entry(spec: CommandSpec, key: str) -> list[str]:
    name = f"{spec.title} ({key})" if key else spec.title
    lines = [f"- **{name}.** {spec.description}."]
    if spec.risk is Risk.CONFIRM:
        lines[0] += " It asks before it does it."
    lines.append("  Say: " + "; ".join(f'"{example}"' for example in spec.examples) + ".")
    return lines


def _app_section(app: str) -> list[str]:
    rows = rows_for_app(app)
    key_for = _KEYS[app]
    offered = [spec for spec in rows if spec.offered]
    never = [spec for spec in rows if not spec.offered]
    lines = [f"## {_APP_NAMES[app]}", ""]
    lines.append(f"{len(offered)} commands can be asked for in a sentence here.")
    lines.append("")
    groups: dict[str, list[CommandSpec]] = {}
    for spec in offered:
        groups.setdefault(spec.group or "Other", []).append(spec)
    for group in sorted(groups):
        lines.extend([f"### {_APP_NAMES[app]}: {group}", ""])
        for spec in sorted(groups[group], key=lambda item: item.title.lower()):
            lines.extend(_entry(spec, key_for(spec.id)))
        lines.append("")
    if never:
        lines.extend([f"### {_APP_NAMES[app]}: only from its menu or key", ""])
        lines.append(
            "These are never done from a sentence, because they send, delete, sign in, "
            "change settings or leave the app. Each is still on its menu and its key."
        )
        lines.append("")
        for spec in sorted(never, key=lambda item: item.title.lower()):
            lines.append(f"- {spec.title}: {spec.where}.")
        lines.append("")
    return lines


def render() -> str:
    lines = [
        "# What you can say in each app",
        "",
        "This page is made from the command catalogue, the one list every QUILL family app "
        "reads to understand what you type or say to it. Do not edit it by hand; run "
        "`python -m quill.tools.build_command_catalogue_reference --write`.",
        "",
        "Each command has a name, its key when it has one, what it does, and some of the ways "
        "you might ask for it. The Command Palette (Ctrl+Shift+P) finds a command by these words "
        "as well as by its name. Commands that change or lose something ask first.",
        "",
    ]
    for app in ("quill", "lite", "radio"):
        lines.extend(_app_section(app))
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render()
    if args.write:
        OUTPUT_PATH.write_bytes(text.encode("utf-8"))
        print(f"OK: wrote {OUTPUT_PATH.relative_to(_ROOT).as_posix()}")
        return 0
    current = OUTPUT_PATH.read_bytes().decode("utf-8") if OUTPUT_PATH.exists() else ""
    if current.replace("\r\n", "\n") != text:
        print("Error: docs/command-catalogue.md is stale; run with --write.")
        return 1
    print("OK: docs/command-catalogue.md matches the catalogue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

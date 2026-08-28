"""Generate the keybinding reference from the keymap itself (GATE-KEYREF).

EdSharp generates ``Hotkeys.md`` from the same table its Key Describer and
menus read: one table, three consumers, and the documentation cannot drift
because nobody writes it. Imported for QUILL 2026-08-27:
``docs/keyboard-reference.md`` is generated from
:data:`quill.core.keymap.DEFAULT_KEYMAP` and
:data:`quill.core.app_keymaps.APP_KEYMAPS` -- the single source of truth for
what is *bound* -- with command titles harvested from the registration
tables the running apps use. A binding added, moved or removed without
regenerating fails the drift gate (``tests/unit/tools/test_keymap_reference.py``).

This documents the **default** keymap; the live, per-user truth is still
Help > Open Keyboard Reference in-app, which renders whatever is actually
bound after customisation. The two agree on day one by construction.

Regenerate::

    python -m quill.tools.build_keymap_reference --write

Check (what the gate runs)::

    python -m quill.tools.build_keymap_reference --check
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.keymap_format import format_binding_for_display

_REPO_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_PATH = _REPO_ROOT / "docs" / "keyboard-reference.md"

#: Where ``register("id", "Title", ...)`` calls and ``("id", "Title",
#: handler)`` tuples name the commands: the whole UI tree, because command
#: registration is spread across the main-frame mixins by design (GATE-11).
_TITLE_SOURCE_DIRS = ("quill/ui",)

_APP_DISPLAY = {"radio": "Quill Radio", "cast": "QUILL Cast"}

#: Section headings for the editor table, by command-id prefix, in the order
#: they should appear. Anything unmatched lands in "Everything else".
_EDITOR_SECTIONS: tuple[tuple[str, str], ...] = (
    ("file.", "Files"),
    ("edit.", "Editing"),
    ("format.", "Formatting"),
    ("navigate.", "Navigation"),
    ("view.", "View"),
    ("speech.", "Speech"),
    ("braille.", "Braille"),
    ("tools.", "Tools"),
    ("ai.", "AI"),
    ("window.", "Windows and Tabs"),
    ("app.", "Application"),
    ("help.", "Help"),
)


def harvest_titles() -> dict[str, str]:
    """Command id -> spoken title, from the registration tables."""
    titles: dict[str, str] = {}
    paths: list[Path] = []
    for rel in _TITLE_SOURCE_DIRS:
        paths.extend(sorted((_REPO_ROOT / rel).rglob("*.py")))
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # commands.register("id", "Title", handler, ...)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("register", "try_register")
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                titles.setdefault(node.args[0].value, node.args[1].value)
            # self._menu_label(_("&Label..."), "command.id") -- the menu is
            # where many commands carry their only human name.
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_menu_label"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                label = _string_of(node.args[0])
                if label:
                    titles.setdefault(node.args[1].value, _clean_menu_label(label))
            # ("id", "Title", handler) palette rows, and ("&Label", "id", ...)
            # app-menu rows.
            elif (
                isinstance(node, ast.Tuple)
                and len(node.elts) >= 2
                and isinstance(node.elts[0], ast.Constant)
                and isinstance(node.elts[0].value, str)
                and isinstance(node.elts[1], ast.Constant)
                and isinstance(node.elts[1].value, str)
            ):
                first, second = node.elts[0].value, node.elts[1].value
                if _looks_like_id(first) and not _looks_like_id(second):
                    titles.setdefault(first, _clean_menu_label(second))
                elif _looks_like_id(second) and not _looks_like_id(first):
                    titles.setdefault(second, _clean_menu_label(first))
    return titles


def _string_of(node: ast.expr) -> str:
    """The literal inside ``"x"`` or ``_("x")``, else ""."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return ""


def _looks_like_id(value: str) -> bool:
    return "." in value and " " not in value and "&" not in value and value == value.lower()


def _clean_menu_label(label: str) -> str:
    return label.replace("&", "").split("\t")[0].strip()


def _title_for(command_id: str, titles: dict[str, str]) -> str:
    title = titles.get(command_id)
    if title:
        return title
    # Fallback for loop-registered families (copy_to_tray_1..12 and kin)
    # whose titles are f-strings the harvest cannot see: readable words from
    # the id itself, which for these families is exactly the runtime title.
    tail = command_id.split(".", 1)[-1].replace("_", " ")
    return tail.capitalize()


def _table(rows: list[tuple[str, str, str]]) -> list[str]:
    lines = ["| Key | Command | Command id |", "| --- | --- | --- |"]
    for binding, title, command_id in rows:
        shown = binding or "(unbound by default)"
        lines.append(f"| {shown} | {title} | `{command_id}` |")
    return lines


def _editor_rows(titles: dict[str, str]) -> list[tuple[str, list[tuple[str, str, str]]]]:
    grouped: dict[str, list[tuple[str, str, str]]] = {label: [] for _, label in _EDITOR_SECTIONS}
    grouped["Everything else"] = []
    for command_id, binding in DEFAULT_KEYMAP.items():
        label = next(
            (name for prefix, name in _EDITOR_SECTIONS if command_id.startswith(prefix)),
            "Everything else",
        )
        display = format_binding_for_display(binding)
        grouped[label].append((display, _title_for(command_id, titles), command_id))
    for rows in grouped.values():
        rows.sort(key=lambda row: (row[0], row[2]))
    return [(label, rows) for label, rows in grouped.items() if rows]


def generate() -> str:
    titles = harvest_titles()
    lines: list[str] = [
        "<!-- AUTO-GENERATED FILE. Do not hand-edit.",
        "    Generated by quill/tools/build_keymap_reference.py from",
        "    quill.core.keymap.DEFAULT_KEYMAP and quill.core.app_keymaps.APP_KEYMAPS.",
        "    To update: python -m quill.tools.build_keymap_reference --write -->",
        "",
        "# QUILL Keyboard Reference (default bindings)",
        "",
        "Generated from the keymap the apps actually load, so this document",
        "cannot drift from the code. Bindings shown as `QUILL Key + <key>` are",
        "chords: press Ctrl+Shift+Grave, release, then the second key. Every",
        "binding here is a *default* -- the in-app reference (Help > Open",
        "Keyboard Reference) always shows your own customised keymap.",
        "",
        f"Editor commands with default bindings: {len(DEFAULT_KEYMAP)}.",
        "",
        "## The QUILL editor",
        "",
    ]
    for label, rows in _editor_rows(titles):
        lines.append(f"### {label}")
        lines.append("")
        lines.extend(_table(rows))
        lines.append("")
    for app_id, keymap in APP_KEYMAPS.items():
        app_name = _APP_DISPLAY.get(app_id, app_id.title())
        lines.append(f"## {app_name} (app keys)")
        lines.append("")
        lines.append(
            "App keys, not editor keys: these apply inside the app named "
            "above and never inside the QUILL editor."
        )
        lines.append("")
        rows = [
            (format_binding_for_display(binding), _title_for(command_id, titles), command_id)
            for command_id, binding in keymap.items()
        ]
        rows.sort(key=lambda row: (row[0], row[2]))
        lines.extend(_table(rows))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="regenerate the reference")
    group.add_argument("--check", action="store_true", help="fail if the reference has drifted")
    args = parser.parse_args(argv)

    fresh = generate()
    if args.write:
        OUTPUT_PATH.write_text(fresh, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT_PATH.relative_to(_REPO_ROOT)}")
        return 0
    committed = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if committed != fresh:
        print(
            "docs/keyboard-reference.md has drifted from the keymap. "
            "Regenerate with: python -m quill.tools.build_keymap_reference --write"
        )
        return 1
    print("keyboard-reference.md matches the keymap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Every menu-bar item in every standalone app shows a keyboard route.

The house rule has been enforced for Quill Radio since 3.0 by walking its real
menu bar (``test_menu_accelerators``). The other six apps had no gate at all,
and a sweep on 2026-08-27 found what no gate finds: **98 menu-bar items across
QUILL Cast, Media Player, Audio Studio, Inkwell, Weather and Converter with no
accelerator whatsoever** -- Cast alone had 46. Every one now carries a key, and
this gate keeps it that way.

Source-level, not runtime: each standalone app builds its whole bar in one
file, so bar membership is decidable by reading it -- a menu variable is a
*bar* menu if it is handed to ``menu_bar.Append``/``Insert``, or hung under one
with ``AppendSubMenu``. Popup menus (tray icons, right-click context menus)
are exempt by that same rule, mechanically: they are never appended to a bar,
and an accelerator on a popup row does nothing anyway.

Also exempt, matching the radio gate: a **disabled status readout** (Cast's
"Podcasts: stopped"), detected by the ``Enable(<same id>, False)`` call beside
it -- there is nothing to invoke, so there is nothing to route to.

What this cannot see -- labels built with f-strings or ``_menu_label`` -- is
what the radio runtime gate exists for; between the two, a keyless bar item
has nowhere left to hide in the apps. The editor's own ``MainFrame`` menus are
out of scope here on purpose: they run through the keymap/menu-customization
system, and their popups (editor context, tray) are popups.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_APPS_DIR = Path(__file__).resolve().parents[3] / "quill" / "apps"

#: Every standalone app's menu-bar file. A new app must join this list -- the
#: coverage test at the bottom fails if a file under quill/apps grows a
#: menu_bar and is not named here.
APP_MENU_FILES = (
    "radio.py",
    "podcasts_menu.py",
    "player.py",
    "studio.py",
    "inkwell.py",
    "weather.py",
    "converter.py",
    "beacon/app.py",
)

_APPEND_KINDS = ("Append", "AppendCheckItem", "AppendRadioItem")


def _bar_menu_vars(tree: ast.AST) -> set[str]:
    """Variable names that end up on a menu bar, submenus included."""
    bar: set[str] = set()
    submenu_edges: list[tuple[str, str]] = []  # (parent var, child var)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        target = node.func.value
        tname = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
        if tname in ("menu_bar", "menubar", "mb") and node.func.attr in ("Append", "Insert"):
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    bar.add(arg.id)
        if node.func.attr == "AppendSubMenu" and node.args:
            child = node.args[0]
            if isinstance(child, ast.Name):
                submenu_edges.append((tname, child.id))
    # Transitive closure: a submenu of a bar menu is a bar menu.
    changed = True
    while changed:
        changed = False
        for parent, child in submenu_edges:
            if parent in bar and child not in bar:
                bar.add(child)
                changed = True
    return bar


def _keyless_bar_items(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    bar = _bar_menu_vars(tree)
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _APPEND_KINDS or len(node.args) < 2:
            continue
        target = node.func.value
        tname = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
        if tname not in bar:
            continue
        label = node.args[1]
        if not isinstance(label, ast.Constant) or not isinstance(label.value, str):
            continue  # dynamic labels are the runtime gate's job
        if "\t" in label.value:
            continue
        # A disabled status readout is exempt: Enable(<same id name>, False).
        id_arg = node.args[0]
        id_name = ""
        if isinstance(id_arg, ast.Attribute):
            id_name = id_arg.attr
        elif isinstance(id_arg, ast.Name):
            id_name = id_arg.id
        if id_name and f"{id_name}, False" in text:
            continue
        findings.append((node.lineno, label.value))
    return findings


@pytest.mark.parametrize("name", APP_MENU_FILES)
def test_every_bar_item_advertises_a_key(name: str) -> None:
    findings = _keyless_bar_items(_APPS_DIR / name)
    assert not findings, f"{name}: menu-bar items with no keyboard route:\n  " + "\n  ".join(
        f"line {line}: {label!r}" for line, label in findings
    )


def test_every_app_with_a_menu_bar_is_covered() -> None:
    """A new app cannot ship outside this gate."""
    covered = {str((_APPS_DIR / name).resolve()) for name in APP_MENU_FILES}
    missing = []
    for path in _APPS_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "menu_bar.Append(" in text or "mb.Append(" in text:
            if str(path.resolve()) not in covered:
                missing.append(path.name)
    assert not missing, f"apps with a menu bar not covered by this gate: {missing}"


def test_the_scanner_is_actually_looking_at_something() -> None:
    """A gate that finds no bar menus passes everything."""
    tree = ast.parse((_APPS_DIR / "podcasts_menu.py").read_text(encoding="utf-8"))
    assert len(_bar_menu_vars(tree)) >= 4

"""No two items in one menu may claim the same Alt letter (bad.md H5).

The menu-bar gate beside this one checks the **titles** -- View, Edit, Tools --
and the item-level accelerator gate checks that every row advertises a shortcut.
Between the two sat the rung nobody walked: the ``&`` letters *inside* a menu.

Windows does not press a duplicated mnemonic. It cycles focus between the
matching items and waits for Enter, so where two rows in one menu claim ``E``,
the letter stops being a shortcut and becomes a slow, silent walk -- and the
person paying for it is the one who navigates menus by letter because reading
the whole menu aloud costs ten seconds. The first sweep found Tools > Customize
offering ``&Export...`` three times and ``&Import...`` twice.

Source-level rather than runtime, for the same reason as the menu-bar gate:
building every menu needs a wx.App and a display, and the literals are what a
reviewer reads and what a regression would change.

Scope: one ``wx.Menu()`` variable inside one function is one menu. That is
exactly how the code is written -- a menu is built in a local, filled, and
appended -- and it means a submenu, which is its own local, is its own
namespace, which is also how Windows treats it.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "quill"

#: Rows that are deliberately keyless. OK, Cancel and Close carry no access key
#: by house rule (GATE-14), and a dynamic row built from a file name cannot.
_APPEND_CALLS = {"Append", "AppendCheckItem", "AppendRadioItem", "AppendSubMenu"}


def _mnemonic(label: str) -> str:
    """The Alt letter a label claims, upper-cased, or ``""``. ``&&`` is a literal."""
    index = label.find("&")
    while index != -1 and label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index == -1 or index + 1 >= len(label):
        return ""
    return label[index + 1].upper()


def _first_labelled_constant(node: ast.AST) -> str | None:
    """The first string literal containing ``&`` anywhere inside *node*.

    Labels arrive in several shapes -- ``_("&New")``, ``self._menu_label(_("&New"),
    "file.new")``, a bare ``"&New"`` -- and all of them carry the letter in the
    first ampersanded literal.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if "&" in child.value:
                return child.value
    return None


def _menus_in(path: Path) -> dict[tuple[str, str], list[tuple[str, int]]]:
    """``(function, menu variable)`` -> the ampersanded labels appended to it."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        menus: set[str] = set()
        for node in ast.walk(function):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                if (
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr == "Menu"
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                ):
                    menus.add(node.targets[0].id)
        for node in ast.walk(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in _APPEND_CALLS:
                continue
            owner = node.func.value
            if not isinstance(owner, ast.Name) or owner.id not in menus:
                continue
            for argument in node.args:
                label = _first_labelled_constant(argument)
                if label is not None:
                    found[(function.name, owner.id)].append((label, node.lineno))
                    break
    return found


def _all_menus() -> dict[str, dict[tuple[str, str], list[tuple[str, int]]]]:
    modules: dict[str, dict[tuple[str, str], list[tuple[str, int]]]] = {}
    for path in sorted(_ROOT.rglob("*.py")):
        menus = _menus_in(path)
        if menus:
            modules[str(path.relative_to(_ROOT.parent)).replace("\\", "/")] = menus
    return modules


def test_no_two_items_in_one_menu_claim_the_same_letter() -> None:
    clashes: list[str] = []
    for module, menus in _all_menus().items():
        for (function, variable), labels in menus.items():
            seen: dict[str, str] = {}
            for label, line in labels:
                letter = _mnemonic(label)
                if not letter:
                    continue
                if letter in seen and seen[letter] != label:
                    clashes.append(
                        f"{module}:{line} {function}/{variable}: Alt+{letter} is both "
                        f"{seen[letter]!r} and {label!r}"
                    )
                seen[letter] = label
    assert not clashes, "two items in one menu claiming one key:\n  " + "\n  ".join(clashes)


def test_the_gate_is_actually_looking_at_something() -> None:
    """A scanner that finds nothing passes everything."""
    menus = _all_menus()
    total = sum(len(labels) for module in menus.values() for labels in module.values())
    assert total >= 200, f"only {total} menu labels found; the scan has stopped seeing the menus"


def test_the_letter_is_read_from_the_label_not_the_first_character() -> None:
    assert _mnemonic("Vi&deo") == "D"
    assert _mnemonic("Save && Close") == ""
    assert _mnemonic("Save && E&xit") == "X"
    assert _mnemonic("No key here") == ""

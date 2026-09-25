"""A list control's rows are data, and wx prints their ampersands literally.

An ``&`` in a button, a checkbox, a static label or a menu item is a mnemonic:
wx eats it and underlines the letter after it. An ``&`` in a row of a
``wx.Choice``, a ``wx.ComboBox`` or a ``wx.ListBox`` is a character: wx prints
it, and a screen reader says "ampersand".

The two are easy to confuse because the strings are written side by side and
often start life as one another. QUILL Lite's Find and Replace dialogs offered
"&Normal", "&Escapes" and "Re&gular expression" in a Search-mode combo for
exactly that reason -- the three had been radio buttons -- and every user saw
and heard the ampersand until 2026-09-09.

Nothing else catches this. It is not a crash, not a layout problem and not a
missing name; the control works perfectly and reads one wrong word per row. So
it is checked here, statically, for the whole tree.

The scan resolves module-level constants as well as literal lists, because that
is how the bug actually appeared: the rows were a module constant and the
``choices=`` expression was a comprehension over it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

#: A lone ampersand before a letter or digit -- a mnemonic. "&&" is an escaped
#: literal ampersand and is not one.
_MNEMONIC = re.compile(r"(?<!&)&(?!&)[A-Za-z0-9]")

#: The controls whose rows are data. wx.RadioBox is deliberately absent: its
#: items *are* control labels and do take mnemonics.
_LIST_CONTROLS = ("Choice", "ComboBox", "ListBox")

_PACKAGE = Path(__file__).resolve().parents[3] / "quill"


def _module_constants(tree: ast.Module) -> dict[str, ast.expr]:
    """Module-level ``NAME = ...`` bindings, so a comprehension can be followed."""
    found: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.value is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            if isinstance(node.target, ast.Name):
                found[node.target.id] = node.value
    return found


def _strings(node: ast.expr) -> list[str]:
    return [
        n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def _offenders() -> list[str]:
    bad: list[str] = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - not our source
            continue
        constants = _module_constants(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            if "RadioBox" in called or not any(c in called for c in _LIST_CONTROLS):
                continue
            for keyword in node.keywords:
                if keyword.arg != "choices":
                    continue
                names = {n.id for n in ast.walk(keyword.value) if isinstance(n, ast.Name)}
                pool = [keyword.value] + [constants[n] for n in names if n in constants]
                offending = sorted({
                    text for expr in pool for text in _strings(expr) if _MNEMONIC.search(text)
                })
                if offending:
                    bad.append(f"{path.relative_to(_PACKAGE.parent)}:{node.lineno}: {offending}")
    return bad


def test_no_list_control_row_carries_a_mnemonic_ampersand() -> None:
    offenders = _offenders()
    assert offenders == [], (
        "These rows go into a Choice, ComboBox or ListBox, where wx prints the "
        "ampersand instead of eating it -- so the row reads '&Normal' on screen "
        "and 'ampersand Normal' out loud. Put the Alt letter on the control's "
        "label instead:\n  " + "\n  ".join(offenders)
    )


def test_the_scan_can_see_the_shape_it_is_looking_for() -> None:
    """A gate that inspects nothing passes everything."""
    source = 'import wx\nROWS = ("&One", "Two")\nwx.Choice(p, choices=[r for r in ROWS])\n'
    tree = ast.parse(source)
    constants = _module_constants(tree)
    assert "ROWS" in constants
    assert any(_MNEMONIC.search(text) for text in _strings(constants["ROWS"]))

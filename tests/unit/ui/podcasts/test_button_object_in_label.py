"""A button in Cast's main window says its object in its label, never in a name.

The survey of 2026-09-30 (qc.md 6b, item 1): on wxMSW a button is self-labelled
and ``set_accessible_name`` is inert on it -- MSAA and UIA never read it -- so
the first "Play what?" fix, which put the object in the accessible name, was
inaudible. The button still said "Play".

This is the gate the plan asked for: no ``set_accessible_name`` call in Cast
targets a ``wx.Button``. Static, by AST, like the other gates. The first test
shows the detector a known-bad sample, because a gate that has never fired
proves nothing; the last walks the live tree.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]

#: Every module of Cast's own UI and its app shell. The rule is about buttons
#: in Cast, not about the main panel alone, so a new dialog cannot reintroduce it.
_CAST_MODULES = sorted([
    *(_ROOT / "quill" / "ui" / "podcasts").glob("*.py"),
    *(_ROOT / "quill" / "apps").glob("podcasts*.py"),
])


def _button_names(tree: ast.AST) -> set[str]:
    """Attribute and local names bound to a ``wx.Button(...)`` anywhere in *tree*."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        func = value.func
        callee = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if callee != "Button":
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                names.add(target.attr)
            elif isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _aliases_of_buttons(tree: ast.AST, buttons: set[str]) -> set[str]:
    """Locals bound to a button attribute: ``button = getattr(self, "_x", None)``
    or ``button = self._x``."""
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        attr = None
        if isinstance(value, ast.Attribute):
            attr = value.attr
        elif (
            isinstance(value, ast.Call)
            and getattr(value.func, "id", "") == "getattr"
            and len(value.args) >= 2
            and isinstance(value.args[1], ast.Constant)
        ):
            attr = str(value.args[1].value)
        if attr in buttons:
            aliases.add(target.id)
    return aliases


def offending_calls(source: str) -> list[int]:
    """Line numbers of ``set_accessible_name(<a wx.Button>, ...)`` in *source*."""
    tree = ast.parse(source)
    buttons = _button_names(tree)
    targets = buttons | _aliases_of_buttons(tree, buttons)
    found: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        callee = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if callee != "set_accessible_name":
            continue
        first = node.args[0]
        name = first.attr if isinstance(first, ast.Attribute) else getattr(first, "id", "")
        if name in targets:
            found.append(node.lineno)
    return found


_BAD = """
import wx
from quill.ui.dialog_contract import set_accessible_name

class Panel:
    def build(self, panel):
        self._play_btn = wx.Button(panel, label="Pla&y")
        set_accessible_name(self._play_btn, "Play Thursday's episode")   # line 8
        other = wx.Button(panel, label="&Add")
        set_accessible_name(other, "Add a podcast")                       # line 10
        text = wx.StaticText(panel, label="Now playing")
        set_accessible_name(text, "Now playing")                          # fine

    def refresh(self):
        button = getattr(self, "_play_btn", None)
        set_accessible_name(button, "Pause")                              # line 16
"""


def test_the_detector_finds_a_name_set_on_a_button_directly_and_through_an_alias() -> None:
    assert offending_calls(_BAD) == [8, 10, 16]


def test_a_name_on_a_static_text_is_not_an_offence() -> None:
    """Static text and trees DO need set_accessible_name; the rule is buttons only."""
    source = 'import wx\ndef b(p):\n    t = wx.StaticText(p)\n    set_accessible_name(t, "x")\n'
    assert offending_calls(source) == []


def test_no_cast_button_is_named_through_set_accessible_name() -> None:
    """The live check. A hit here is a button whose object is inaudible on
    Windows: put the object in the label instead (core/transport_button.py)."""
    hits = []
    for path in _CAST_MODULES:
        for line in offending_calls(path.read_text(encoding="utf-8")):
            hits.append(f"{path.relative_to(_ROOT).as_posix()}:{line}")
    assert hits == [], "set_accessible_name on a wx.Button is inert on wxMSW: " + ", ".join(hits)


def test_the_gate_covers_every_cast_module() -> None:
    names = {p.name for p in _CAST_MODULES}
    assert {"main_panel.py", "places.py", "podcasts.py"} <= names

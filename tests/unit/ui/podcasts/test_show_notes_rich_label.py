"""Show Notes' formatted view has its own label (qc.md 6b item 14).

On wxMSW a control's accessible name is the ``wx.StaticText`` created
immediately before it. "Show notes:" was consumed by the plain-text field, so
the formatted ``HtmlWindow`` after it announced with no name. It now has its
own label, created right before it, and the label is shown and hidden with
the view so a sighted reader never sees a heading over nothing.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SOURCE = (
    Path(__file__).resolve().parents[4] / "quill" / "ui" / "podcasts" / "show_notes_dialog.py"
).read_text(encoding="utf-8")


def _constructions(tree: ast.AST) -> list[tuple[int, str, str]]:
    """(line, constructor, assigned attribute) for each ``self.x = wx...(...)``."""
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        func = node.value.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        target = node.targets[0]
        attr = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
        found.append((node.lineno, name, attr))
    return sorted(found)


def test_the_formatted_view_is_constructed_immediately_after_its_own_label() -> None:
    built = _constructions(ast.parse(_SOURCE))
    index = next(i for i, (_l, name, _a) in enumerate(built) if name == "HtmlWindow")
    _line, before, attr = built[index - 1]
    assert (before, attr) == ("StaticText", "_rich_label")


def test_the_label_follows_the_view_when_it_is_shown_and_hidden() -> None:
    assert "self._rich_label.Hide()" in _SOURCE
    assert "self._rich_label.Show(rich_selected)" in _SOURCE


def test_the_label_has_an_access_key_of_its_own() -> None:
    assert 'label="Show notes, &formatted:"' in _SOURCE

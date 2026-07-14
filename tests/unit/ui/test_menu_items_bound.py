"""Guard against menu items that are appended but never bound to a handler.

A menu item created with ``menu.Append(self._id_x, ...)`` does nothing on click
unless something also calls ``frame.Bind(wx.EVT_MENU, handler, id=self._id_x)``.
The id->command map in ``_command_to_menu_id_map`` only feeds the accelerator
table (keyboard shortcuts), not menu dispatch, so a missing ``Bind`` leaves the
item dead — this is exactly how "AI Library..." and "Ask Quill by Voice..."
silently stopped opening.

This static check parses the menu-building mixins, collects every ``self._id_*``
appended as a menu item, and asserts each is bound (by ``id=`` keyword or third
positional arg) somewhere in the same set of modules. A small allowlist covers
ids that are intentionally dispatched through a shared catch-all ``EVT_MENU``
handler (the dynamic recent-files / sessions submenus) rather than by id.
"""

from __future__ import annotations

import ast
from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"
_MODULES = [
    _UI / "main_frame_menu.py",
    _UI / "main_frame.py",
    _UI / "main_frame_github.py",
    _UI / "main_frame_devtools.py",
    _UI / "main_frame_ssh.py",
    _UI / "main_frame_sessions.py",
]

# Ids handled by a shared catch-all EVT_MENU handler (dynamic submenus) instead
# of a per-id Bind. These check ``event.GetId()`` against the id at runtime.
_CATCH_ALL_DISPATCHED = {"_id_clear_recent", "_id_clear_recent_sessions"}


def _self_id_attr(node: ast.AST) -> str | None:
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
        and node.attr.startswith("_id_")
    ):
        return node.attr
    return None


def test_appended_menu_items_are_bound() -> None:
    appended: dict[str, tuple[str, int]] = {}
    bound: set[str] = set()

    for module in _MODULES:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            method = node.func.attr
            if method in ("Append", "AppendCheckItem", "AppendRadioItem") and node.args:
                attr = _self_id_attr(node.args[0])
                if attr is not None:
                    appended.setdefault(attr, (module.name, node.lineno))
            elif method == "Bind":
                for kw in node.keywords:
                    if kw.arg == "id":
                        attr = _self_id_attr(kw.value)
                        if attr is not None:
                            bound.add(attr)
                if len(node.args) >= 3:
                    attr = _self_id_attr(node.args[2])
                    if attr is not None:
                        bound.add(attr)

    missing = {
        attr: loc
        for attr, loc in appended.items()
        if attr not in bound and attr not in _CATCH_ALL_DISPATCHED
    }
    assert not missing, (
        "menu items appended but never bound to an EVT_MENU handler "
        f"(add a frame.Bind(..., id=...)): {missing}"
    )

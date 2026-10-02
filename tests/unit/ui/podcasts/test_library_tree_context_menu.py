"""Shift+F10 on Cast's library tree opens the row menu its help promises.

The survey of 2026-09-30 (qc.md 6b, item 3): only ``EVT_TREE_ITEM_MENU`` was
bound, and Shift+F10 and the Applications key can arrive as a bare
``EVT_CONTEXT_MENU`` -- so the tree's own help taught a key that opened nothing.
Radio met the same defect on 2026-08-16 (aaed65f) and bound both.

Two checks: the panel binds both events to the one handler; and that handler
builds its menu from the *selection*, never from the event, so a keyboard
request (which carries no item) gets the same menu a right-click does.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parents[4]
_PANEL = _ROOT / "quill" / "ui" / "podcasts" / "main_panel.py"


def _bound_events(source: str, handler: str) -> set[str]:
    """Event names bound to ``self.<handler>`` on ``self._shows_tree``.

    Understands both ``tree.Bind(wx.EVT_X, self.h)`` and the loop form
    ``for e in (wx.EVT_X, wx.EVT_Y): tree.Bind(e, self.h)``.
    """
    events: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple):
            loop_events = {e.attr for e in node.iter.elts if isinstance(e, ast.Attribute)}
            for inner in ast.walk(node):
                if _is_bind_to(inner, handler):
                    events |= loop_events
        elif _is_bind_to(node, handler) and isinstance(node.args[0], ast.Attribute):
            events.add(node.args[0].attr)
    return events


def _is_bind_to(node: ast.AST, handler: str) -> bool:
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return False
    if node.func.attr != "Bind" or len(node.args) < 2:
        return False
    target = node.args[1]
    return isinstance(target, ast.Attribute) and target.attr == handler


def test_both_context_menu_routes_reach_the_one_handler() -> None:
    events = _bound_events(_PANEL.read_text(encoding="utf-8"), "_on_library_context_menu")
    assert {"EVT_TREE_ITEM_MENU", "EVT_CONTEXT_MENU"} <= events


def test_the_detector_sees_a_single_bind_too() -> None:
    source = "def b(self, wx):\n    self._shows_tree.Bind(wx.EVT_TREE_ITEM_MENU, self.h)\n"
    assert _bound_events(source, "h") == {"EVT_TREE_ITEM_MENU"}


def test_the_handler_builds_its_menu_from_the_selection_not_the_event(monkeypatch) -> None:
    """A keyboard request carries no item; the menu must not depend on one."""
    from quill.apps import podcasts_library_actions as actions

    popped: list[list[str]] = []

    class _Menu:
        def __init__(self) -> None:
            self.labels: list[str] = []

        def Append(self, _id, label):  # noqa: N802 - wx API shape
            self.labels.append(label)

        def Bind(self, *_a, **_k):  # noqa: N802
            pass

        def Destroy(self):  # noqa: N802
            pass

    fake_wx = SimpleNamespace(Menu=_Menu, NewIdRef=object, EVT_MENU="EVT_MENU")
    monkeypatch.setattr(actions, "wx", fake_wx)
    host = SimpleNamespace(
        _library_context_entries=lambda: [("&Play Next Episode", lambda: None)],
        _keep_menu_ids=lambda *_ids: None,
        _shows_tree=SimpleNamespace(PopupMenu=lambda menu: popped.append(menu.labels)),
    )
    handler = actions.CastLibraryActionsMixin._on_library_context_menu
    handler(host, None)  # what a bare EVT_CONTEXT_MENU amounts to: no item
    handler(host, SimpleNamespace(GetItem=lambda: None))
    assert popped == [["&Play Next Episode"], ["&Play Next Episode"]]

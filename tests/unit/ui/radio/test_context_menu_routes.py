"""Every way of asking for a row's menu has to reach the same row.

Shift+F10 and the Applications key were reported dead on the browse tree
(2026-08-16): the menu opened on right-click and did nothing from the
keyboard. ``EVT_TREE_ITEM_MENU`` names its item by hit-testing the *mouse*,
so a keyboard request -- which has no mouse over a row -- handed back an
invalid item and the handler returned before building anything.

These tests pin the three routes: right-click (item supplied), keyboard
(no item, no position), and a positioned context-menu event (hit-test).
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio.browse_tree_menu import target_node


class _Item:
    def __init__(self, name: str, ok: bool = True) -> None:
        self.name = name
        self._ok = ok

    def IsOk(self) -> bool:  # noqa: N802 - wx spelling
        return self._ok

    def __repr__(self) -> str:
        return f"<{self.name}>"


class _Position:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Position) and (self.x, self.y) == (other.x, other.y)


DEFAULT_POSITION = _Position(-1, -1)


class _Wx:
    DefaultPosition = DEFAULT_POSITION


class _Tree:
    def __init__(self, selected: Any = None, hit: Any = None) -> None:
        self._selected = selected
        self._hit = hit
        self.hit_tested = False

    def GetSelection(self) -> Any:  # noqa: N802 - wx spelling
        return self._selected

    def ScreenToClient(self, position: Any) -> Any:  # noqa: N802 - wx spelling
        return position

    def HitTest(self, _position: Any) -> tuple[Any, int]:  # noqa: N802 - wx spelling
        self.hit_tested = True
        return self._hit, 0


class _Dialog:
    def __init__(self, tree: _Tree) -> None:
        self._wx = _Wx()
        self._tree = tree


class _Event:
    """A context-menu event. Any of its accessors may be absent, as in wx."""

    def __init__(self, item: Any = None, position: Any = None) -> None:
        if item is not None:
            self._item = item
        if position is not None:
            self._position = position

    def GetItem(self) -> Any:  # noqa: N802 - wx spelling
        return getattr(self, "_item", None)

    def GetPosition(self) -> Any:  # noqa: N802 - wx spelling
        return getattr(self, "_position", None)


def test_right_click_uses_the_row_it_hit() -> None:
    row = _Item("clicked")
    tree = _Tree(selected=_Item("selected"))
    assert target_node(_Dialog(tree), _Event(item=row)) is row


def test_shift_f10_falls_back_to_the_selected_row() -> None:
    # The reported bug: no item, no position, so the menu never opened.
    selected = _Item("selected")
    tree = _Tree(selected=selected)
    event = _Event(item=_Item("invalid", ok=False), position=DEFAULT_POSITION)
    assert target_node(_Dialog(tree), event) is selected


def test_the_applications_key_sends_no_item_at_all() -> None:
    selected = _Item("selected")
    tree = _Tree(selected=selected)
    assert target_node(_Dialog(tree), _Event()) is selected


def test_a_positioned_event_hit_tests_that_point() -> None:
    under_mouse = _Item("under mouse")
    tree = _Tree(selected=_Item("selected"), hit=under_mouse)
    event = _Event(position=_Position(40, 90))
    assert target_node(_Dialog(tree), event) is under_mouse
    assert tree.hit_tested


def test_a_point_that_hits_nothing_still_falls_back_to_the_selection() -> None:
    selected = _Item("selected")
    tree = _Tree(selected=selected, hit=_Item("nothing", ok=False))
    assert target_node(_Dialog(tree), _Event(position=_Position(40, 90))) is selected


def test_an_empty_tree_offers_no_row_rather_than_raising() -> None:
    tree = _Tree(selected=_Item("none", ok=False))
    assert target_node(_Dialog(tree), _Event()) is None

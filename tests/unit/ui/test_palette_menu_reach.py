"""The palette's menu-bar half, without a frame: titles, skips and rebuilds."""

from __future__ import annotations

from quill.core.commands import CommandRegistry
from quill.ui.palette_menu_reach import (
    MENU_COMMAND_PREFIX,
    plain_menu_text,
    register_menu_items,
)


class _Item:
    def __init__(self, item_id, label, submenu=None, separator=False):
        self._id, self._label, self._sub, self._sep = item_id, label, submenu, separator

    def GetId(self):
        return self._id

    def GetItemLabel(self):
        return self._label

    def GetSubMenu(self):
        return self._sub

    def IsSeparator(self):
        return self._sep


class _Menu:
    def __init__(self, *items):
        self._items = list(items)

    def GetMenuItems(self):
        return self._items


class _Bar:
    def __init__(self, *menus):
        self._menus = list(menus)

    def GetMenuCount(self):
        return len(self._menus)

    def GetMenuLabel(self, index):
        return self._menus[index][0]

    def GetMenu(self, index):
        return self._menus[index][1]


def _bar():
    imports = _Menu(_Item(11, "&Word Document...\tCtrl+Alt+W"), _Item(12, "&PDF (Alt+F, I, P)"))
    file_menu = _Menu(
        _Item(1, "&New\tCtrl+N"),
        _Item(2, "", separator=True),
        _Item(3, "&Import", submenu=imports),
        _Item(4, "Recent: notes.txt"),
    )
    return _Bar(("&File", file_menu))


def test_plain_menu_text_drops_mnemonic_key_route_and_dots() -> None:
    assert plain_menu_text("&Word Document...\tCtrl+Alt+W") == "Word Document"
    assert plain_menu_text("&PDF (Alt+F, I, P)") == "PDF"
    assert plain_menu_text("Fish && &Chips") == "Fish & Chips"


def test_uncovered_items_become_rows_titled_by_their_path() -> None:
    registry = CommandRegistry()
    ran: list[int] = []
    added = register_menu_items(registry, _bar(), covered_ids={1}, post_menu_event=ran.append)
    titles = {c.id: c.title for c in registry.list()}
    assert added == 3
    assert titles == {
        f"{MENU_COMMAND_PREFIX}11": "File > Import > Word Document",
        f"{MENU_COMMAND_PREFIX}12": "File > Import > PDF",
        f"{MENU_COMMAND_PREFIX}4": "File > Recent: notes.txt",
    }
    assert registry.get(f"{MENU_COMMAND_PREFIX}11").keybinding == "Ctrl+Alt+W"
    registry.run(f"{MENU_COMMAND_PREFIX}12")
    assert ran == [12]


def test_a_rebuild_replaces_the_previous_rows() -> None:
    registry = CommandRegistry()
    register_menu_items(registry, _bar(), covered_ids=(), post_menu_event=lambda _i: None)
    smaller = _Bar(("&File", _Menu(_Item(1, "&New"))))
    register_menu_items(registry, smaller, covered_ids=(), post_menu_event=lambda _i: None)
    assert [c.id for c in registry.list()] == [f"{MENU_COMMAND_PREFIX}1"]

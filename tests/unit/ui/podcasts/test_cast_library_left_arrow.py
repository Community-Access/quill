"""Left Arrow collapses tree rows without moving focus to Places."""

from __future__ import annotations

from typing import Any

from quill.apps.podcasts import PodcastsAppFrame


class _Item:
    def IsOk(self) -> bool:
        return True


class _Tree:
    def __init__(self, data: tuple[str, str], *, expanded: bool) -> None:
        self.item = _Item()
        self.data = data
        self.expanded = expanded
        self.collapsed: list[Any] = []
        self.root = object()

    def GetSelection(self) -> _Item:
        return self.item

    def GetItemData(self, _item: _Item) -> tuple[str, str]:
        return self.data

    def IsExpanded(self, _item: _Item) -> bool:
        return self.expanded

    def Collapse(self, item: _Item) -> None:
        self.collapsed.append(item)

    def GetItemParent(self, _item: _Item) -> object:
        return self.root

    def GetRootItem(self) -> object:
        return self.root


class _Places:
    def __init__(self) -> None:
        self.focused = False

    def focus(self) -> None:
        self.focused = True


class _Event:
    def __init__(self, code: int) -> None:
        self.code = code
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self.code

    def AltDown(self) -> bool:
        return False

    def Skip(self) -> None:
        self.skipped = True


class _Host:
    def __init__(self, tree: _Tree) -> None:
        self._shows_tree = tree
        self._places = _Places()

    def _library_find_active(self) -> bool:
        return False


def test_left_collapses_an_expanded_root_folder_without_focusing_places() -> None:
    import wx

    tree = _Tree(("folder", "folder-id"), expanded=True)
    host = _Host(tree)
    event = _Event(wx.WXK_LEFT)

    PodcastsAppFrame._on_library_key(host, event)

    assert tree.collapsed == [tree.item]
    assert not host._places.focused
    assert not event.skipped


def test_left_from_a_root_podcast_stays_in_the_tree() -> None:
    import wx

    tree = _Tree(("show", "show-id"), expanded=False)
    host = _Host(tree)
    event = _Event(wx.WXK_LEFT)

    PodcastsAppFrame._on_library_key(host, event)

    assert not host._places.focused
    assert tree.collapsed == []
    assert event.skipped


def test_left_from_a_collapsed_root_folder_stays_in_the_tree() -> None:
    import wx

    tree = _Tree(("folder", "folder-id"), expanded=False)
    host = _Host(tree)
    event = _Event(wx.WXK_LEFT)

    PodcastsAppFrame._on_library_key(host, event)

    assert not host._places.focused
    assert tree.collapsed == []
    assert event.skipped


def test_left_on_an_expanded_show_is_left_to_native_tree_navigation() -> None:
    import wx

    tree = _Tree(("show", "show-id"), expanded=True)
    host = _Host(tree)
    event = _Event(wx.WXK_LEFT)

    PodcastsAppFrame._on_library_key(host, event)

    assert not host._places.focused
    assert tree.collapsed == []
    assert event.skipped

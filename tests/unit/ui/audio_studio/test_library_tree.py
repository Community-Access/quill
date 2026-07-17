"""Headless build smoke for the Audio Studio library tree widget (Phase 2)."""

from __future__ import annotations

import pytest

from quill.core.audio_studio.library import BookEntry, LibraryState
from quill.ui.audio_studio.library_tree import build_library_tree


@pytest.fixture
def app():
    import wx

    a = wx.App(False)
    yield a
    a.Destroy()


def test_build_library_tree_smoke(app) -> None:
    import wx

    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
    state = LibraryState(
        books=[
            BookEntry(path="a", title="Alpha", favorite=True),
            BookEntry(path="b", title="Beta", folder="Fiction"),
            BookEntry(path="c", title="Gamma", folder="Fiction/SF"),
        ],
        folders=["Fiction", "Fiction/SF"],
    )
    build_library_tree(tree, state)
    assert tree.GetCount() > 0
    frame.Destroy()


def test_build_library_tree_tags_book_and_view_items(app) -> None:
    import wx

    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
    state = LibraryState(
        books=[BookEntry(path="a", title="Alpha", favorite=True)],
        folders=[],
    )
    build_library_tree(tree, state)
    root = tree.GetRootItem()
    kinds: set[str] = set()

    def walk(item):
        if not item.IsOk():
            return
        data = tree.GetItemData(item)
        if isinstance(data, tuple) and len(data) == 2:
            kinds.add(data[0])
        child, _cookie = tree.GetFirstChild(item)
        while child.IsOk():
            walk(child)
            child, _cookie = tree.GetNextChild(item, _cookie)

    walk(root)
    assert "view" in kinds
    assert "book" in kinds
    frame.Destroy()


def test_build_library_tree_preserves_selection(app) -> None:
    import wx

    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
    state = LibraryState(books=[BookEntry(path="a", title="Alpha")], folders=[])
    build_library_tree(tree, state)
    # Find the book item and select it, then rebuild keeping that key.
    keep_key = ("book", "a")
    build_library_tree(tree, state, keep_key=keep_key)
    sel = tree.GetSelection()
    assert sel.IsOk()
    assert tree.GetItemData(sel) == keep_key
    frame.Destroy()

"""Headless build smoke for the Audio Studio library tree widget (Phase 2)."""

from __future__ import annotations

import pytest

from quill.core.audio_studio.library import BookEntry, LibraryState
from quill.ui.audio_studio.library_tree import LibraryTreeActions, build_library_tree


def _view_children(tree, view_name):
    """Return the (kind, key) tags of the books under a named pinned view."""
    root = tree.GetRootItem()
    child, cookie = tree.GetFirstChild(root)
    while child.IsOk():
        if tree.GetItemData(child) == ("view", view_name):
            found = []
            bchild, bcookie = tree.GetFirstChild(child)
            while bchild.IsOk():
                found.append(tree.GetItemData(bchild))
                bchild, bcookie = tree.GetNextChild(child, bcookie)
            return found
        child, cookie = tree.GetNextChild(root, cookie)
    return None


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


def test_pinned_views_are_populated(app) -> None:
    """Regression: the Favorites/In Progress/Recently Played views must list
    their books, not render as empty headers."""
    import wx

    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
    state = LibraryState(
        books=[
            BookEntry(path="a", title="Alpha", favorite=True, last_played_at=10.0),
            BookEntry(path="b", title="Beta"),
        ],
        folders=[],
    )
    build_library_tree(tree, state)
    assert ("book", "a") in _view_children(tree, "Favorites")
    assert ("book", "a") in _view_children(tree, "Recently Played")
    # A never-played, non-favorite book is in neither of those views.
    assert ("book", "b") not in _view_children(tree, "Favorites")
    frame.Destroy()


def test_toggle_favorite_ingests_an_unknown_book(app) -> None:
    """Favoriting a book that only exists as an Inbox entry adds it to the
    library so the favorite actually persists (and the announcement is true)."""
    store = LibraryState(books=[], folders=[])
    inbox_entry = BookEntry(path="/inbox/x.m4b", title="Inbox Book")
    said: list[str] = []
    ok = LibraryTreeActions.toggle_favorite(store, inbox_entry, announce=said.append)
    assert ok
    assert [b.path for b in store.books] == ["/inbox/x.m4b"]
    assert store.books[0].favorite is True
    assert said == ["Added Inbox Book to Favorites"]


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

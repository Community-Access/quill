"""Headless build smoke for the Audio Studio library tree widget (Phase 2)."""

from __future__ import annotations

import pytest

from quill.core.audio_studio.library import BookEntry, LibraryState
from quill.ui.audio_studio.library_tree import LibraryTreeActions, build_library_tree
from tests.wx_session import shared_wx_app


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

    a = shared_wx_app()
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


def _select(tree, parent_tag, tag) -> None:
    from quill.ui.audio_studio.library_tree import _rows

    tree.SelectItem(next(row[3] for row in _rows(tree) if row[:2] == (parent_tag, tag)))


def _here(tree):
    item = tree.GetSelection()
    return tree.GetItemData(tree.GetItemParent(item)), tree.GetItemData(item)


def test_the_reader_stays_on_the_copy_of_a_book_they_were_on(app) -> None:
    # FUX-06: a book shows under Favorites and under its folder. A reload after
    # a background job used to land on the last copy, not the one being read.
    import wx

    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
    state = LibraryState(
        books=[BookEntry(path="a", title="Alpha", favorite=True, folder="Fiction")],
        folders=["Fiction"],
    )
    build_library_tree(tree, state)
    _select(tree, ("view", "Favorites"), ("book", "a"))
    item = tree.GetSelection()
    build_library_tree(tree, state, keep_key=("book", "a"))  # nothing changed
    assert tree.GetSelection() == item, "an unchanged library is not redrawn"
    state.books.append(BookEntry(path="b", title="Beta"))
    build_library_tree(tree, state, keep_key=("book", "a"))
    assert _here(tree) == (("view", "Favorites"), ("book", "a"))
    frame.Destroy()


def test_a_removed_book_lands_on_its_neighbour_not_the_first_view(app) -> None:
    import wx

    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
    books = [BookEntry(path=p, title=t) for p, t in (("a", "Alpha"), ("b", "Beta"), ("c", "Gamma"))]
    state = LibraryState(books=list(books))
    build_library_tree(tree, state)
    _select(tree, None, ("book", "b"))
    state.books.remove(books[1])
    build_library_tree(tree, state, keep_key=("book", "b"))
    assert _here(tree) == (None, ("book", "c"))
    frame.Destroy()


def test_the_library_window_can_fill_the_tree_it_is_handed(app, monkeypatch) -> None:
    # ensure_library_window calls reload_tree(tree) before the host remembers
    # the tree; the host's method took no argument, so the window failed to open.
    import wx

    import quill.apps.studio as studio

    monkeypatch.setattr(studio, "load_library", lambda _dir: LibraryState(books=[]))
    host = studio.StudioAppFrame.__new__(studio.StudioAppFrame)
    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame)
    studio.StudioAppFrame._reload_library_tree(host, tree)
    assert tree.GetCount() > 0
    frame.Destroy()


def test_a_book_moved_to_a_folder_is_followed_there(app) -> None:
    import wx

    frame = wx.Frame(None)
    tree = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
    book = BookEntry(path="a", title="Alpha")
    state = LibraryState(books=[book, BookEntry(path="b", title="Beta")], folders=["Fiction"])
    build_library_tree(tree, state)
    _select(tree, None, ("book", "a"))
    book.folder = "Fiction"
    build_library_tree(tree, state)
    assert _here(tree) == (("folder", "Fiction"), ("book", "a"))
    frame.Destroy()

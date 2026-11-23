"""Audio Studio library tree widget + actions (Phase 2 port-in).

The shared ``wx.TreeCtrl`` builder for the standalone Studio's "Your books"
panel (and available to any embedded surface that wants a library browser).
Mirrors the shape of ``quill/apps/podcasts.py:_reload_library_tree``: a hidden
root, one child per pinned view, nested ``"/"``-separated folder items, then
books sorted by title under their folder. Each item is tagged
``(kind, key)`` via ``SetItemData`` so the host can route activation / context
menus / keys without re-deriving the selection.

``LibraryTreeActions`` mirrors ``quill/ui/podcasts/show_actions.py``: one
implementation of favorite / move / new folder / delete behind every surface
that acts on a book, so wording and announcements stay identical. ``open_book``
and ``reveal_in_workbench`` are announcement passthroughs -- the host owns the
actual workbench-open wiring -- so the shared widget stays shell-agnostic.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.audio_studio.library import (
    PINNED_VIEWS,
    BookEntry,
    LibraryState,
    add_book,
    view_query,
)
from quill.core.audio_studio.library import (
    move_to_folder as _move_to_folder,
)
from quill.core.audio_studio.library import (
    toggle_favorite as _toggle_favorite,
)
from quill.core.list_follow import land
from quill.core.recent import remove_recent_audiobook_file

TOP_LEVEL_CHOICE = "(Top level -- no folder)"
NEW_FOLDER_CHOICE = "(New folder...)"

#: Item-data key shape: (kind, key). kind in {"view", "folder", "book"}.
TreeKey = tuple[str, str]


def _rows(tree: wx.TreeCtrl) -> list[tuple[object, object, str, object]]:
    """Every item top to bottom: (parent's tag, own tag, label, item)."""
    rows: list[tuple[object, object, str, object]] = []

    def walk(parent: object) -> None:
        child, cookie = tree.GetFirstChild(parent)
        while child.IsOk():
            rows.append((
                tree.GetItemData(parent),
                tree.GetItemData(child),
                tree.GetItemText(child),
                child,
            ))
            walk(child)
            child, cookie = tree.GetNextChild(parent, cookie)

    root = tree.GetRootItem()
    if root.IsOk():
        walk(root)
    return rows


def _fill(tree: wx.TreeCtrl, state: LibraryState) -> None:
    """Root "Library", the pinned views with their books, then the folders and books."""
    root = tree.AddRoot("Library")
    for view in PINNED_VIEWS:
        view_item = tree.AppendItem(root, view)
        tree.SetItemData(view_item, ("view", view))
        # Populate the view with the books its query returns. Without this the
        # four views rendered as permanently empty headers -- the reason the
        # home library looked broken. Books also appear under their folder
        # below; a pinned view is a cross-cutting saved search, so a book can
        # legitimately show under Favorites/Recently Played and under its folder.
        for book in view_query(state, view):
            tree.SetItemData(tree.AppendItem(view_item, book.title), ("book", book.path))

    folder_items: dict[str, object] = {"": root}

    def folder_item(folder: str) -> object:
        if folder in folder_items:
            return folder_items[folder]
        segments = folder.split("/")
        parent_path = "/".join(segments[:-1])
        parent = folder_item(parent_path) if parent_path else root
        item = tree.AppendItem(parent, segments[-1])
        tree.SetItemData(item, ("folder", folder))
        folder_items[folder] = item
        return item

    for folder in sorted(state.folders):
        folder_item(folder)
    for book in sorted(state.books, key=lambda b: b.title.casefold()):
        parent = folder_item(book.folder) if book.folder else root
        tree.SetItemData(tree.AppendItem(parent, book.title), ("book", book.path))
    tree.ExpandAll()


def build_library_tree(
    tree: wx.TreeCtrl,
    state: LibraryState,
    *,
    keep_key: TreeKey | None = None,
) -> None:
    """Rebuild ``tree`` from ``state``, keeping the reader where they were (FUX-06).

    Root "Library" (hidden by the host via ``TR_HIDE_ROOT`` if desired), then
    pinned views, then nested folders, then books sorted by title under their
    folder (or at root when ``folder == ""``).

    A book can show twice -- under Favorites and under its folder -- so the
    reader is found by the item *and* its parent, not the first copy with the
    same tag. A book that has gone lands them on the row that moved into its
    place, not the first view. A rebuild that would change nothing is skipped,
    so a background job finishing does not make the screen reader read the
    row again. *keep_key* moves the reader to that item instead.
    """
    before = _rows(tree)
    item = tree.GetSelection()
    at = next((i for i, row in enumerate(before) if row[3] == item), -1) if item.IsOk() else -1
    here = (before[at][0], before[at][1]) if at >= 0 else None
    moving = keep_key is not None and (here is None or here[1] != keep_key)
    tag = keep_key if moving else (here[1] if here is not None else None)
    scratch = _Shape()
    _fill(scratch, state)  # type: ignore[arg-type]
    if before and _by_parent(before) == _by_parent(scratch.rows) and not moving:
        return  # nothing changed: not redrawn, so nothing is read again
    tree.Freeze()
    try:
        tree.DeleteAllItems()
        _fill(tree, state)
    finally:
        tree.Thaw()
    after = _rows(tree)
    keys = [repr((row[0], row[1])) for row in after]
    wanted = repr(here) if here is not None and not moving else None
    if wanted not in keys and tag is not None:
        # The same book (or folder) under another parent -- moved to a folder,
        # or asked for by key: its first copy.
        wanted = next((k for k, row in zip(keys, after, strict=True) if row[1] == tag), wanted)
    if wanted is None and before:
        return  # the reader was on nothing, and stays on nothing
    index = land(keys, wanted, at).index if keys else -1
    if index >= 0:
        tree.SelectItem(after[index][3])


def _by_parent(rows: list[Any]) -> dict[str, list[str]]:
    """Each parent's children, in order: what a reader would meet."""
    shape: dict[str, list[str]] = {}
    for row in rows:
        shape.setdefault(repr(row[0]), []).append(repr((row[1], row[2])))
    return shape


class _Shape:
    """A stand-in tree that only records what :func:`_fill` would show."""

    def __init__(self) -> None:
        self.rows: list[tuple[object, object, str]] = []
        self._tags: dict[int, object] = {}
        self._next = 0

    def AddRoot(self, _label: str) -> int:  # noqa: N802 - wx shape
        return self._new(None)

    def AppendItem(self, parent: int, label: str) -> int:  # noqa: N802
        item = self._new(None)
        self.rows.append((self._tags.get(parent), item, label))
        return item

    def SetItemData(self, item: int, tag: object) -> None:  # noqa: N802
        self._tags[item] = tag
        self.rows = [
            (parent, tag if own == item else own, label) for parent, own, label in self.rows
        ]

    def ExpandAll(self) -> None:  # noqa: N802
        return None

    def _new(self, tag: object) -> int:
        self._next += 1
        self._tags[self._next] = tag
        return self._next


def selected_key(tree: wx.TreeCtrl) -> TreeKey | None:
    """Return the ``(kind, key)`` tagged on the current selection, or None."""
    item = tree.GetSelection()
    if not item.IsOk():
        return None
    data = tree.GetItemData(item)
    return data if isinstance(data, tuple) and len(data) == 2 else None


class LibraryTreeActions:
    """Shared book/folder actions behind every library-tree surface."""

    @staticmethod
    def toggle_favorite(
        store: LibraryState,
        entry: BookEntry,
        *,
        announce: Callable[[str], None],
    ) -> bool:
        # Ingest first: acting on a book (including an Inbox entry that only
        # lives in the recent-files list) promotes it into the library, so the
        # toggle actually takes effect and the announcement is truthful. Without
        # this, favoriting an Inbox book announced success but changed nothing.
        add_book(store, entry.path, entry.title)
        now_fav = _toggle_favorite(store, entry.path)
        verb = "Added" if now_fav else "Removed"
        prep = "to" if now_fav else "from"
        announce(f"{verb} {entry.title} {prep} Favorites")
        return True

    @staticmethod
    def new_folder(
        parent: object,
        store: LibraryState,
        *,
        announce: Callable[[str], None],
    ) -> bool:
        entry = wx.TextEntryDialog(parent, "New folder name:", "New Folder")
        try:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return False
            name = entry.GetValue().strip()
        finally:
            entry.Destroy()
        if not name or name in store.folders:
            return False
        store.folders.append(name)
        announce(f"Created folder {name}")
        return True

    @staticmethod
    def move_to_folder(
        parent: object,
        store: LibraryState,
        entry: BookEntry,
        *,
        announce: Callable[[str], None],
    ) -> bool:
        """Pick (or create) the folder this book lives in."""
        folders = sorted(store.folders, key=lambda f: f.casefold())
        choices = [TOP_LEVEL_CHOICE, *folders, NEW_FOLDER_CHOICE]
        picker = wx.SingleChoiceDialog(
            parent,
            "Where should this book live?",
            f"Move {entry.title} to Folder",
            choices,
        )
        try:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return False
            choice = picker.GetStringSelection()
        finally:
            picker.Destroy()
        if choice == NEW_FOLDER_CHOICE:
            if not LibraryTreeActions.new_folder(parent, store, announce=lambda _m: None):
                return False
            choice = store.folders[-1]
        # Ingest first (see toggle_favorite): filing an Inbox book into a folder
        # promotes it into the library so the move actually persists.
        add_book(store, entry.path, entry.title)
        if choice == TOP_LEVEL_CHOICE:
            _move_to_folder(store, entry.path, "")
            announce(f"Filed {entry.title} at the top level")
            return True
        _move_to_folder(store, entry.path, choice)
        announce(f"Filed {entry.title} under {choice}")
        return True

    @staticmethod
    def delete_book(
        parent: object,
        store: LibraryState,
        entry: BookEntry,
        *,
        announce: Callable[[str], None],
    ) -> bool:
        """Remove a book from the library and the audiobook MRU (file untouched)."""
        confirm = wx.MessageDialog(
            parent,
            f"Remove {entry.title} from your library?",
            "Remove Book",
            style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        try:
            if confirm.ShowModal() != wx.ID_YES:  # dialog_button_contract: exempt
                return False
        finally:
            confirm.Destroy()
        store.books = [b for b in store.books if b.path != entry.path]
        try:
            remove_recent_audiobook_file(Path(entry.path))
        except Exception:  # noqa: BLE001 - MRU tidy must not block the delete
            pass
        announce(f"Removed {entry.title} from the library")
        return True

    @staticmethod
    def open_book(
        entry: BookEntry,
        *,
        announce: Callable[[str], None],
    ) -> bool:
        """Announce the open; the host performs the actual workbench open."""
        announce(f"Opening {entry.title}")
        return True

    @staticmethod
    def reveal_in_workbench(
        entry: BookEntry,
        *,
        announce: Callable[[str], None],
    ) -> bool:
        """Announce the reveal; the host performs the actual workbench reveal."""
        announce(f"Revealing {entry.title} in the Chapter Workbench")
        return True

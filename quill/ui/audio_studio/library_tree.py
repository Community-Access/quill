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
from quill.core.recent import remove_recent_audiobook_file

TOP_LEVEL_CHOICE = "(Top level -- no folder)"
NEW_FOLDER_CHOICE = "(New folder...)"

#: Item-data key shape: (kind, key). kind in {"view", "folder", "book"}.
TreeKey = tuple[str, str]


def build_library_tree(
    tree: wx.TreeCtrl,
    state: LibraryState,
    *,
    keep_key: TreeKey | None = None,
) -> None:
    """Rebuild ``tree`` from ``state``, preserving the ``keep_key`` selection.

    Root "Library" (hidden by the host via ``TR_HIDE_ROOT`` if desired), then
    pinned views, then nested folders, then books sorted by title under their
    folder (or at root when ``folder == ""``).
    """
    tree.DeleteAllItems()
    root = tree.AddRoot("Library")
    select_item: object = None

    def tag(item: object, key: TreeKey) -> None:
        nonlocal select_item
        tree.SetItemData(item, key)
        if key == keep_key:
            select_item = item

    for view in PINNED_VIEWS:
        view_item = tree.AppendItem(root, view)
        tag(view_item, ("view", view))
        # Populate the view with the books its query returns. Without this the
        # four views rendered as permanently empty headers -- the reason the
        # home library looked broken. Books also appear under their folder
        # below; a pinned view is a cross-cutting saved search, so a book can
        # legitimately show under Favorites/Recently Played and under its folder.
        for book in view_query(state, view):
            tag(tree.AppendItem(view_item, book.title), ("book", book.path))

    folder_items: dict[str, object] = {"": root}

    def folder_item(folder: str) -> object:
        if folder in folder_items:
            return folder_items[folder]
        segments = folder.split("/")
        parent_path = "/".join(segments[:-1])
        parent = folder_item(parent_path) if parent_path else root
        item = tree.AppendItem(parent, segments[-1])
        tag(item, ("folder", folder))
        folder_items[folder] = item
        return item

    for folder in sorted(state.folders):
        folder_item(folder)

    for book in sorted(state.books, key=lambda b: b.title.casefold()):
        parent = folder_item(book.folder) if book.folder else root
        tag(tree.AppendItem(parent, book.title), ("book", book.path))

    tree.ExpandAll()
    first, _cookie = tree.GetFirstChild(root)
    if select_item is not None:
        tree.SelectItem(select_item)
    elif first.IsOk():
        tree.SelectItem(first)


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

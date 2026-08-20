"""Removing a favourite, and where the cursor goes afterwards.

Extracted from :mod:`quill.ui.radio.favorites_manager_dialog` under GATE-11
when the cursor-landing work pushed that module past its budget. It is a real
seam rather than a size dodge: *what to delete* is the dialog's business, and
*where the listener ends up* is a rule shared with the Recordings Manager
(:mod:`quill.core.radio.list_cursor`) that neither dialog should own privately.

The landing key has to be worked out **before** the removal. A ``wx.TreeCtrl`` is
rebuilt wholesale on every change, so the caller cannot ask for "row 3"
afterwards -- it has to know which *item* to look for. Without that,
``_refresh_tree`` fell through to "select the first item", and deleting the
fortieth favourite read out the first with focus still in the tree
(2026-08-19).
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.list_cursor import neighbour_key


def display_keys(
    store: RadioFavoritesStore, *, query: str, sort: str, folder_sorts: dict
) -> list[str]:
    """Every station key in the order the tree is currently showing them.

    The filtered view is a flat list of matches and the unfiltered one is the
    stored display order, so "what comes next" means two different things and
    the search box decides which.
    """
    if query:
        return [favorite.key for favorite in store.search(query)]
    return [favorite.key for favorite in store.favorites_in_display_order(sort, folder_sorts)]


def landing_after_removal(
    store: RadioFavoritesStore, *, removed: str, query: str, sort: str, folder_sorts: dict
) -> str | None:
    """The favourite to select once *removed* is gone. ``None`` when none is left."""
    return neighbour_key(
        display_keys(store, query=query, sort=sort, folder_sorts=folder_sorts), removed
    )


def landing_after_folder_delete(
    store: RadioFavoritesStore, *, path: str, sort: str, folder_sorts: dict
) -> str | None:
    """The first station that is about to step out of folder *path*.

    Deleting a folder never deletes stations -- they line up at the top level in
    the same order. Landing on the first of them keeps the cursor beside the
    content the listener was looking at, rather than at the top of the whole
    collection.
    """
    return next(
        (
            favorite.key
            for favorite in store.favorites_in_display_order(sort, folder_sorts)
            if favorite.folder == path or favorite.folder.startswith(f"{path}/")
        ),
        None,
    )


def remove_selected(dialog: Any) -> None:
    """Remove the selected favourite and leave the cursor somewhere real."""
    from quill.ui.radio.favorite_actions import remove_favorite

    favorite = dialog._selected_favorite()
    if favorite is None:
        return
    key = favorite.key
    # Worked out before the removal -- see this module's docstring for why.
    landing = landing_after_removal(dialog._store, removed=key, **dialog._cursor_args())
    if not remove_favorite(dialog.dialog, dialog._store, favorite, announce=dialog._announce):
        return
    if dialog._marked_key == key:
        dialog._marked_key = None
    dialog._changed(keep_key=landing)
    if landing is None:
        dialog._announce("No favorites left.")


def confirm_folder_delete(wx: Any, parent: Any, path: str) -> bool:
    """Ask before deleting a folder, saying plainly that nothing is lost."""
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation inside a managed dialog
        f"Delete the folder {path}?\n\n"
        "Your stations are completely safe: they simply step out of the "
        "folder and line up at the top level of your favorites, in the "
        "same order. Nothing leaves your collection.",
        "Delete Folder",
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    return bool(answer == wx.YES)

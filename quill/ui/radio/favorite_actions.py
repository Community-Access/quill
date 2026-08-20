"""Shared favorite-station actions (rename / remove / move to folder).

One implementation behind every surface that acts on a favorite -- the
Favorites Manager dialog and the standalone main panel's tree -- so the
dialogs, wording, and announcements stay identical everywhere.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore

TOP_LEVEL_CHOICE = "(Top level -- no folder)"
NEW_FOLDER_CHOICE = "(New folder...)"


def rename_favorite(
    parent: object,
    store: RadioFavoritesStore,
    favorite: FavoriteStation,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Prompt for a custom display name; blank restores the directory's own."""
    import wx

    entry = wx.TextEntryDialog(
        parent,
        f"Your name for this station (leave blank to use {favorite.station.display_name}):",
        "Rename Station",
        value=favorite.custom_name,
    )
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue().strip()
    finally:
        entry.Destroy()
    store.rename(favorite.key, name)
    if name:
        announce(f"Station renamed to {name}.")
    else:
        announce(f"Station name restored to {favorite.station.display_name}.")
    return True


def remove_favorite(
    parent: object,
    store: RadioFavoritesStore,
    favorite: FavoriteStation,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then remove the favorite from the store.

    The confirmation carries a **Don't ask me again** checkbox (2026-08-18):
    removing a favorite is small and undone by adding it back, and somebody
    tidying a long list answers the same question a dozen times. The answer is
    remembered in the shared ask-prefs store, so Delete on the row and Remove
    from the context menu -- which both arrive here -- go quiet together.
    """
    from quill.core.podcasts.ask_prefs import REMOVE_FAVORITE_KEY
    from quill.ui.confirm_once_dialog import confirm_once

    name = favorite.display_label
    if not confirm_once(
        parent,
        title="Remove Favorite",
        message=f"Remove {name} from your favorites?",
        affirmative="&Remove",
        question_key=REMOVE_FAVORITE_KEY,
        announce=announce,
        quiet_note="removing a favorite",
    ):
        return False
    store.remove(favorite.key)
    announce(f"Removed {name} from favorites.")
    return True


def remove_all_favorites(
    parent: object,
    store: RadioFavoritesStore,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then remove every favorite from the store (#1201).

    Folders are left intact. A backup is snapshotted on save, so this is
    recoverable; the confirmation says so. Returns True if anything was removed.
    """
    import wx

    count = len(store.favorites)
    if count == 0:
        announce("You have no favorites to remove.")
        return False
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Remove all {count} favorite(s)? Folders are kept, and a backup is saved "
        "so this can be undone from your favorites backups.",
        "Remove All Favorites",
        wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    if answer != wx.YES:
        return False
    removed = store.clear()
    announce(f"Removed all {removed} favorite(s).")
    return True


def move_favorite_to_folder(
    parent: object,
    store: RadioFavoritesStore,
    favorite: FavoriteStation,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Pick (or create, with / nesting) the folder this station lives in."""
    import wx

    choices = [TOP_LEVEL_CHOICE, *store.folder_names(), NEW_FOLDER_CHOICE]
    picker = wx.SingleChoiceDialog(
        parent,
        "Where should this station live? Choose a folder, the top level, "
        "or create a new folder (use / to nest, like News/Morning).",
        f"Move {favorite.display_label} to Folder",
        choices,
    )
    try:
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        choice = picker.GetStringSelection()
    finally:
        picker.Destroy()
    if choice == NEW_FOLDER_CHOICE:
        entry = wx.TextEntryDialog(
            parent,
            "New folder path (use / to nest, like News/Morning):",
            "New Folder",
        )
        try:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return False
            choice = entry.GetValue().strip().strip("/")
        finally:
            entry.Destroy()
        if not choice:
            return False
    folder = "" if choice == TOP_LEVEL_CHOICE else choice
    store.set_folder(favorite.key, folder)
    announce(f"Filed {favorite.display_label} under {folder or 'the top level'}.")
    return True


def rename_folder_prompt(
    parent: object,
    store: RadioFavoritesStore,
    folder_path: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Rename the last segment of *folder_path*, carrying descendants along."""
    import wx

    parent_path, _, current = folder_path.rpartition("/")
    entry = wx.TextEntryDialog(parent, "Folder name:", "Rename Folder", value=current)
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue().strip().strip("/")
    finally:
        entry.Destroy()
    if not name or name == current:
        return False
    new_path = f"{parent_path}/{name}" if parent_path else name
    touched = store.rename_folder(folder_path, new_path)
    announce(f"Folder renamed to {name}; {touched} station(s) came along.")
    return True


def delete_folder_prompt(
    parent: object,
    store: RadioFavoritesStore,
    folder_path: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then dissolve the folder -- its stations are never deleted."""
    import wx

    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Delete the folder {folder_path}?\n\n"
        "Your stations are completely safe: they simply step out of the "
        "folder and line up at the top level of your favorites, in the "
        "same order. Nothing leaves your collection.",
        "Delete Folder",
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    if answer != wx.YES:
        return False
    moved = store.delete_folder(folder_path)
    announce(f"Folder {folder_path} deleted; {moved} station(s) moved to the top level.")
    return True


def create_folder_prompt(
    parent: object,
    store: RadioFavoritesStore,
    *,
    announce: Callable[[str], None],
    initial_parent: str = "",
) -> bool:
    """New Folder...: pick where it lives, then name it.

    The folder exists immediately (before any station is filed into it) and
    shows up in every tree and picker. Nesting works two ways: choose a
    parent folder in the location list, or type / in the name.
    """
    import wx

    existing = store.folder_names()
    choices = [TOP_LEVEL_CHOICE, *existing]
    picker = wx.SingleChoiceDialog(
        parent,
        "Where should the new folder live?",
        "New Folder -- Location",
        choices,
    )
    try:
        if initial_parent and initial_parent in existing:
            picker.SetSelection(existing.index(initial_parent) + 1)
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        location = picker.GetStringSelection()
    finally:
        picker.Destroy()
    parent_path = "" if location == TOP_LEVEL_CHOICE else location
    entry = wx.TextEntryDialog(parent, "Folder name:", "New Folder")
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue().strip().strip("/")
    finally:
        entry.Destroy()
    if not name:
        return False
    path = f"{parent_path}/{name}" if parent_path else name
    if not store.add_folder(path):
        announce(f"A folder named {path} already exists.")
        return False
    announce(f"Created folder {path}. File stations into it with Move to Folder.")
    return True

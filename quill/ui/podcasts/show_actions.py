"""Shared show/folder actions (favorite / move / unsubscribe / folder CRUD).

One implementation behind every surface that acts on a subscribed show --
today the standalone QUILL Cast main panel's tree; the Podcast Manager
dialog keeps its own long-established equivalents for now -- so wording and
announcements for a given action stay identical wherever it's added next.
Mirrors the shape of ``quill/ui/radio/favorite_actions.py``, adapted to
podcasts' id-based folder tree (``PodcastFolder.id``/``parent_folder_id``)
rather than radio favorites' string-path folders.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

TOP_LEVEL_CHOICE = "(Top level -- no folder)"
NEW_FOLDER_CHOICE = "(New folder...)"


def toggle_favorite(
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> None:
    show.is_favorite = not show.is_favorite
    verb = "Added" if show.is_favorite else "Removed"
    preposition = "to" if show.is_favorite else "from"
    announce(f"{verb} {show.title} {preposition} Favorites")


def move_show_to_folder(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Pick (or create) the library folder this show lives in."""
    import wx

    folders = sorted(library.folders, key=lambda f: f.name.casefold())
    choices = [TOP_LEVEL_CHOICE, *(f.name for f in folders), NEW_FOLDER_CHOICE]
    picker = wx.SingleChoiceDialog(
        parent,
        "Where should this show live?",
        f"Move {show.title} to Folder",
        choices,
    )
    try:
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        choice = picker.GetStringSelection()
    finally:
        picker.Destroy()
    if choice == NEW_FOLDER_CHOICE:
        entry = wx.TextEntryDialog(parent, "New folder name:", "New Folder")
        try:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return False
            name = entry.GetValue().strip()
        finally:
            entry.Destroy()
        if not name:
            return False
        folder_id = library.add_folder(name).id
    elif choice == TOP_LEVEL_CHOICE:
        folder_id = None
    else:
        match = next((f for f in folders if f.name == choice), None)
        folder_id = match.id if match is not None else None
    show.folder_id = folder_id
    label = next((f.name for f in library.folders if f.id == folder_id), None)
    announce(f"Filed {show.title} under {label or 'the top level'}")
    return True


def rename_folder_prompt(
    parent: object,
    library: PodcastLibrary,
    folder_id: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    import wx

    folder = library.find_folder(folder_id)
    if folder is None:
        return False
    entry = wx.TextEntryDialog(parent, "Folder name:", "Rename Folder", value=folder.name)
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue().strip()
    finally:
        entry.Destroy()
    if not name or name == folder.name:
        return False
    folder.name = name
    announce(f"Folder renamed to {name}")
    return True


def delete_folder_prompt(
    parent: object,
    library: PodcastLibrary,
    folder_id: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then dissolve the folder -- its shows are never unsubscribed."""
    import wx

    folder = library.find_folder(folder_id)
    if folder is None:
        return False
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Delete the folder {folder.name}?\n\n"
        "Your shows are completely safe: they simply step out of the folder "
        "and land at the top level of your library. Nothing is unsubscribed.",
        "Delete Folder",
        wx.ICON_QUESTION | wx.YES_NO,
        parent,
    )
    if answer != wx.YES:
        return False
    moved = library.delete_folder(folder_id, contents="promote")
    announce(f"Folder {folder.name} deleted; shows moved to the top level.")
    return bool(moved) or True


def create_folder_prompt(
    parent: object,
    library: PodcastLibrary,
    *,
    announce: Callable[[str], None],
    initial_parent_id: str | None = None,
) -> bool:
    """New Folder...: pick where it lives, then name it.

    The folder exists immediately (before any show is filed into it) and
    shows up in every tree and picker.
    """
    import wx

    folders = sorted(library.folders, key=lambda f: f.name.casefold())
    choices = [TOP_LEVEL_CHOICE, *(f.name for f in folders)]
    picker = wx.SingleChoiceDialog(
        parent,
        "Where should the new folder live?",
        "New Folder -- Location",
        choices,
    )
    try:
        if initial_parent_id:
            names = [f.name for f in folders]
            match = next((f for f in folders if f.id == initial_parent_id), None)
            if match is not None:
                picker.SetSelection(names.index(match.name) + 1)
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        location = picker.GetStringSelection()
    finally:
        picker.Destroy()
    parent_id = None
    if location != TOP_LEVEL_CHOICE:
        match = next((f for f in folders if f.name == location), None)
        parent_id = match.id if match is not None else None
    entry = wx.TextEntryDialog(parent, "Folder name:", "New Folder")
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue().strip()
    finally:
        entry.Destroy()
    if not name:
        return False
    library.add_folder(name, parent_folder_id=parent_id)
    announce(f"Created folder {name}. File shows into it with Move to Folder.")
    return True


def unsubscribe_show_prompt(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then unsubscribe -- optionally deleting downloaded episodes
    per the show's (or library default's) delete-files-on-remove policy."""
    import wx

    downloaded = [e for e in show.episodes if e.downloaded_path]
    policy = library.effective_settings(show).delete_files_on_remove
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Unsubscribe from {show.title}?",
        "Unsubscribe",
        wx.ICON_QUESTION | wx.YES_NO,
        parent,
    )
    if answer != wx.YES:
        return False
    delete_files = policy == "always"
    if downloaded and policy == "ask":
        delete_files = (
            wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
                f"Also delete the {len(downloaded)} downloaded episode file(s)?",
                "Delete Downloaded Files",
                wx.ICON_QUESTION | wx.YES_NO,
                parent,
            )
            == wx.YES
        )
    if delete_files:
        for episode in downloaded:
            path = Path(episode.downloaded_path)
            if path.exists():
                path.unlink(missing_ok=True)
    library.remove_show(show.id)
    if delete_files and downloaded:
        announce(f"Unsubscribed from {show.title} and deleted its downloaded episodes")
    else:
        announce(f"Unsubscribed from {show.title}")
    return True

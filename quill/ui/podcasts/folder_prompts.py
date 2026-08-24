"""Naming things in the podcast library: folders, and saved views.

Five prompts that all ask the same shape of question -- what should this be
called, where does it go, and is it safe to remove -- extracted from
``show_actions.py`` under GATE-11 when that module (the shared home of every
podcast verb) reached its cap. They stay re-exported from there, so no caller
had to move with them.

Every one of them announces its outcome, including the refusals: a rename
that quietly did nothing because the name was taken is indistinguishable
from a key that did not register.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.subscriptions import PodcastLibrary

TOP_LEVEL_CHOICE = "(Top level -- no folder)"
NEW_FOLDER_CHOICE = "(New folder...)"


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


def rename_view_prompt(
    parent: object,
    library: PodcastLibrary,
    view_id: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Give a pinned library view (Favorites, New Episodes, ...) a personal
    name. The shipped views are the app's, so the name is always resettable --
    entering a blank, or the shipped label itself, IS the reset."""
    import wx

    from quill.core.podcasts import virtual_views

    if view_id not in virtual_views.DEFAULT_VIEW_LABELS:
        return False
    shipped = virtual_views.DEFAULT_VIEW_LABELS[view_id]
    current = virtual_views.view_label(library, view_id)
    entry = wx.TextEntryDialog(
        parent,
        f"Your name for the {shipped} view (blank to use the standard name):",
        "Rename View",
        value=current,
    )
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue()
    finally:
        entry.Destroy()
    if not virtual_views.set_view_name(library, view_id, name):
        return False
    now = virtual_views.view_label(library, view_id)
    if now == shipped:
        announce(f"{current} is back to its standard name, {shipped}.")
    else:
        announce(f"{shipped} view renamed to {now}")
    return True


def reset_view_name_action(
    library: PodcastLibrary,
    view_id: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Reset Name on a renamed pinned view: back to the shipped label."""
    from quill.core.podcasts import virtual_views

    current = virtual_views.view_label(library, view_id)
    if not virtual_views.reset_view_name(library, view_id):
        return False
    shipped = virtual_views.view_label(library, view_id)
    announce(f"{current} is back to its standard name, {shipped}.")
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
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
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

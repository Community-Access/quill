"""Deleting a folder, and the two questions that has to ask first.

Extracted from ``manager_dialog`` under GATE-11. It is a real seam rather than
a line-count convenience: everything here is about **what happens to what is
inside**, which is the only genuinely dangerous thing the folder tree can do.

Two questions, in this order, and both default to the safe answer:

1. Do the podcasts inside move up a level, or get unsubscribed with the folder?
   "Move them up" is offered first and is labelled safe, because a folder is an
   arrangement and deleting an arrangement should not delete the things
   arranged.
2. If they were unsubscribed, do their downloaded files go too? That one is
   ``NO_DEFAULT``: somebody pressing Enter reflexively must not lose audio.
"""

from __future__ import annotations

from typing import Any

from quill.ui.dialog_contract import show_message_box

__all__ = ["delete_folder"]


def delete_folder(dialog: Any, folder: Any) -> None:
    import wx

    from quill.core.podcasts.follow_words import following_count

    with wx.SingleChoiceDialog(  # dialog_button_contract: exempt
        dialog.dialog,
        f'What should happen to the podcasts inside "{folder.name}"?',
        "Delete Folder",
        [
            "Move them up to the parent folder (safe)",
            "Unfollow them too",
        ],
    ) as picker:
        if picker.ShowModal() != wx.ID_OK:
            return
        contents = "promote" if picker.GetSelection() == 0 else "remove"
    removed = dialog._library.delete_folder(folder.id, contents=contents)
    deleted_files = 0
    if removed:
        confirm = show_message_box(
            "Also delete the downloaded episodes of the "
            f"{following_count(len(removed))} you stopped following?",
            "Delete Downloaded Files",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            dialog.dialog,
            announce=dialog._announce,
        )
        if confirm == wx.YES:
            deleted_files = dialog._delete_downloaded_files_for_removed_shows(removed)
    dialog._on_library_changed()
    dialog.refresh_tree()
    if removed:
        suffix = f" and {deleted_files} downloaded file(s) deleted" if deleted_files else ""
        dialog._announce(
            f"Folder {folder.name} deleted; stopped following "
            f"{following_count(len(removed))}{suffix}"
        )
    else:
        dialog._announce(f"Folder {folder.name} deleted; its contents moved up")

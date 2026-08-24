"""Deleting a recording, and where the cursor goes afterwards.

Extracted from :mod:`quill.ui.radio.recordings_manager_dialog` under GATE-11
when the cursor-landing work pushed that module past its budget, and it is the
right seam for the same reason as :mod:`quill.ui.radio.favorites_delete`:
*which* file to delete is the dialog's business, and *where the listener ends
up* is a rule shared with the Favorites Manager.

The manager's refresh restores its selection **by identity**, which is exactly
right for a status flip (Recording -> Recorded keeps the same path) and exactly
wrong for a deletion -- a deleted row has no identity left, so the list came
back with no selection and no focused row at all, and arrowing started again
from the top (2026-08-19).
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.list_cursor import index_after_removal
from quill.core.radio.recordings_index import STATUS_RECORDING


def confirm(wx: Any, parent: Any, entry: Any) -> bool:
    """Ask before deleting, naming the file and its size."""
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation inside a managed dialog
        f"Delete the recording {entry.name}?\n\nThis removes the file "
        f"({entry.size_display}) from your recordings folder permanently.",
        "Remove Recording",
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    return bool(answer == wx.YES)


def remove_selected(dialog: Any) -> None:
    """Delete the selected recording and leave the cursor somewhere real."""
    entry = dialog._selected()
    if entry is None or entry.path is None:
        return
    if entry.status == STATUS_RECORDING:
        dialog._announce("Still recording; stop it before removing it.")
        return
    removed_index = dialog._list.GetFirstSelected()
    if not confirm(dialog._wx, dialog.dialog, entry):
        return
    from quill.ui import undo_last_ui

    # Moved aside, not unlinked, so Ctrl+Z brings the recording itself back
    # and not just its name (11.3). Without an app owning undo this is still
    # an ordinary delete.
    held = undo_last_ui.hold_or_delete([entry.path])
    if not held and entry.path.exists():
        try:
            entry.path.unlink()
        except OSError as error:
            dialog._announce(f"Could not delete the file: {error}.")
            return

    def _undo() -> None:
        undo_last_ui.restore(held)
        dialog._refresh(keep_selection=False)

    undo_last_ui.remember(
        "Delete Recording",
        entry.name,
        entry.size_display,
        _undo,
        dispose=lambda: undo_last_ui.discard(held),
    )
    dialog._announce(undo_last_ui.offer(f"Removed recording {entry.name}."))
    dialog._refresh(keep_selection=True)
    target = index_after_removal(removed_index, dialog._list.GetItemCount())
    if target is None:
        dialog._announce("No recordings left.")
        return
    dialog._list.Select(target)
    dialog._list.Focus(target)
    dialog._list.EnsureVisible(target)
    dialog._on_selection_changed()

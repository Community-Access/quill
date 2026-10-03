"""The one name prompt: new folder, rename folder, rename place (qc.md section 6).

Six raw ``TextEntryDialog`` sites asked for a name in six slightly different
ways and none of them went through the dialog contract, so none announced
its surface and none was in the inventory (6b). This is the one prompt they
share: through ``apply_modal_ids``, announcing its title on the way in, and
returning the trimmed name or None.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["folder_name_prompt", "name_prompt"]


def name_prompt(
    parent: Any,
    title: str,
    current: str = "",
    *,
    announce: Callable[[str], None] | None = None,
    message: str = "Name:",
) -> str | None:
    """Ask for a name. None when cancelled or left blank."""
    import wx

    from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

    dialog = wx.TextEntryDialog(
        parent, message, title, value=current
    )  # dialog_button_contract: exempt
    try:
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        answer = show_modal_dialog(dialog, title, announce=announce)
        if answer != wx.ID_OK:
            return None
        name = dialog.GetValue().strip()
    finally:
        dialog.Destroy()
    return name or None


def folder_name_prompt(
    parent: Any, *, current: str = "", announce: Callable[[str], None] | None = None
) -> str | None:
    """ "New Folder" or "Rename Folder", by whether there is a current name."""
    title = "Rename Folder" if current else "New Folder"
    return name_prompt(parent, title, current, announce=announce, message="Folder name:")

"""A sync conflict's two versions, read before choosing one (FUX-12).

Sync History listed each conflict as its beacon, its field and a message,
and asked for Use Local, Use Remote or Use Merged without either version in
sight. The selected conflict now shows below the list as lines of text: what
this device has, what the other device has, the difference between them
marked in the Diff Line Marks style every QUILL diff shares, and what Use
Merged would keep. Nothing is said as the list moves (the reader says the
row); Tab reaches the versions.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.dpi import dip_size

__all__ = ["add_conflict_detail", "conflict_text", "show_selected_conflict"]


def conflict_text(conflict: dict[str, Any]) -> str:
    """The conflict in words: both versions, their differences, and the merge."""
    from quill.core.diff_marks import render_texts
    from quill.core.github.review_preferences import load_line_marks

    field = str(conflict.get("field") or "note")
    local = str(conflict.get("local") or "")
    remote = str(conflict.get("remote") or "")
    merged = str(conflict.get("merged") or "")
    lines = [
        f"The {field} of {conflict.get('entity_id', 'this beacon')} was changed on both devices.",
        "Lines marked as removed are only in this device's version; lines marked as "
        "added are only in the other device's.",
        "",
        render_texts(
            local,
            remote,
            "this device's version",
            "the other device's version",
            style=load_line_marks(),
        ),
        "",
        "This device's version (Use Local):",
        local or "(empty)",
        "",
        "The other device's version (Use Remote):",
        remote or "(empty)",
        "",
        "Use Merged keeps both: the other device's lines, and this device's removed "
        "lines kept in the note with a marker you can edit out:",
        _readable_merge(merged) or "(empty)",
    ]
    return "\n".join(lines)


_MARKER = "<<<<<< local removed: "


def _readable_merge(merged: str) -> str:
    """The merge with its marker said in words rather than a row of "<"."""
    return "\n".join(
        f"Kept, marked as removed on this device: {line[len(_MARKER) :]}"
        if line.startswith(_MARKER)
        else line
        for line in merged.split("\n")
    )


def add_conflict_detail(parent: wx.Window, sizer: wx.Sizer) -> wx.TextCtrl:
    """The read-only box under the conflicts list that shows the selected one."""
    sizer.Add(wx.StaticText(parent, label="Selected conflict, both &versions:"), 0, wx.ALL, 8)
    detail = wx.TextCtrl(
        parent,
        style=wx.TE_MULTILINE | wx.TE_READONLY,
        size=dip_size(parent, -1, 140),
    )
    detail.SetName("Selected conflict, both versions")
    detail.SetHelpText(
        "The selected conflict as text: this device's version, the other device's, "
        "each line that differs marked as removed or added, and what Use Merged keeps. "
        "Read it before choosing Use Local, Use Remote or Use Merged."
    )
    sizer.Add(detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    return detail


def show_selected_conflict(dialog: Any) -> None:
    """Show Sync History's selected conflict, the first when none is selected.

    With none left the box says so and the three Use buttons are dimmed; focus
    on one of them first moves to the list, never to a dimmed button.
    """
    if dialog.conflict_list.GetSelection() < 0 and dialog._conflicts:
        dialog.conflict_list.SetSelection(0)
    sel = dialog.conflict_list.GetSelection()
    ok = 0 <= sel < len(dialog._conflicts)
    text = conflict_text(dialog._conflicts[sel]) if ok else "No conflicts need review."
    dialog.conflict_detail.SetValue(text)
    buttons = (dialog.r_local, dialog.r_remote, dialog.r_merged)
    if not ok and wx.Window.FindFocus() in buttons:
        dialog.conflict_list.SetFocus()
    for button in buttons:
        button.Enable(ok)

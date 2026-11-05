"""The Forms windows that the shared WordPress windows do not already cover (17a.4).

Most Forms questions reuse the WordPress windows -- a list window with
buttons, a report, a choice, a question, and the generated block form
(:func:`quill.ui.wordpress_block_dialogs.ask_fields`) -- so a person who has
learned one has learned these. What is new here:

- the **Form Outline** is the WordPress list window with the outline's own
  keys: Alt+Shift+Up and Down move a question, Alt+Shift+Right and Left move
  it into or out of a section (17a.4.3);
- **Insert Field's list** is the list window with a search box, returning
  the kind chosen;
- **Form Properties** is the generated form with a read-only box under it
  for what the site decides (17a.4.5);
- **Save the New Form** is the standard Save As window, opened on a ``.bfl``
  name.

*show_modal* is the host's own modal runner, so the dialog contract and the
dialog inventory see these the way they see every other window.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import wx

from quill.core.forms.menu import FORM_EXTENSION
from quill.ui import wordpress_dialogs as dlg
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

#: Alt+Shift+arrow -> the outline action it presses (17a.4.3).
OUTLINE_KEYS: dict[int, str] = {
    wx.WXK_UP: "Move &Up",
    wx.WXK_DOWN: "Move &Down",
    wx.WXK_RIGHT: "Move &In",
    wx.WXK_LEFT: "Move Ou&t",
}


def show_outline_window(parent: wx.Window, show_modal: dlg.ShowModal, **kwargs: Any) -> Any:
    """The list window, with Alt+Shift and the arrows pressing the move buttons."""
    window = dlg.ListWindow(parent, **kwargs)
    window.rows.Bind(wx.EVT_KEY_DOWN, lambda event: _outline_key(window, event))
    show_modal(window, str(kwargs.get("title", "")))
    return window


def _outline_key(window: Any, event: wx.KeyEvent) -> None:
    label = OUTLINE_KEYS.get(event.GetKeyCode())
    if label and event.AltDown() and event.ShiftDown() and not event.ControlDown():
        for action, button in zip(window._actions, window.buttons, strict=True):
            if action.label == label and button.IsEnabled():
                window._run(action)
                return
        wx.Bell()
        return
    event.Skip()


def ask_save_path(
    parent: wx.Window, show_modal: dlg.ShowModal, *, title: str, suggested: str
) -> Path | None:
    """Where to save a new form: the standard Save As window, on a form file name."""
    name = suggested.strip() or "form"
    dialog = wx.FileDialog(
        parent,
        message=title,
        defaultFile=_file_name(name),
        wildcard=f"Forms (*{FORM_EXTENSION})|*{FORM_EXTENSION}|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        path = Path(dialog.GetPath())
    finally:
        dialog.Destroy()
    return (
        path
        if str(path).lower().endswith(FORM_EXTENSION)
        else path.with_name(path.name + FORM_EXTENSION)
    )


def ask_properties(
    parent: wx.Window,
    show_modal: dlg.ShowModal,
    *,
    title: str,
    purpose: str,
    fields: Sequence[Any],
    facts: str,
) -> dict[str, Any] | None:
    """Form Properties: the generated form, then what is the site's to set, read only."""
    from quill.ui.wordpress_block_dialogs import BlockFormDialog

    dialog = BlockFormDialog(parent, title=title, purpose=purpose, fields=fields, ok_label="OK")
    about = wx.TextCtrl(dialog, value=facts, style=wx.TE_MULTILINE | wx.TE_READONLY)
    about.SetHelpText(
        "What the site decides for this form: spam protection, notifications and where it is "
        "published. Read it line by line; it changes nothing here."
    )
    about.SetMinSize(dip_size(dialog, 420, 90))
    sizer = dialog.GetSizer()
    label = wx.StaticText(dialog, label="On the site (read only):")
    set_spoken_name(about, "On the site (read only)")
    sizer.Insert(sizer.GetItemCount() - 1, label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    sizer.Insert(sizer.GetItemCount() - 1, about, 0, wx.EXPAND | wx.ALL, 8)
    label.MoveBeforeInTabOrder(about)
    about.MoveBeforeInTabOrder(dialog.FindWindow(wx.ID_OK))
    dialog.Fit()
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dict(dialog.answers())
    finally:
        dialog.Destroy()


def _file_name(title: str) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else " " for c in title)
    return " ".join(keep.split())[:60] + FORM_EXTENSION


def pick_from_list(
    parent: wx.Window,
    show_modal: dlg.ShowModal,
    *,
    title: str,
    purpose: str,
    list_label: str,
    list_help: str,
    rows: list[str],
    filter_label: str,
    filter_help: str,
    matches: Callable[[str, int], bool],
    details: Callable[[int], str],
) -> int | None:
    """A searchable list (Insert Field's types): Enter or Choose picks; the index, or None."""
    shown = list(range(len(rows)))
    picked: list[int] = []

    def narrow(query: str) -> list[str]:
        shown[:] = [i for i in range(len(rows)) if matches(query, i)]
        return [rows[i] for i in shown]

    def choose(index: int | None) -> object:
        if index is None or index >= len(shown):
            return None
        picked.append(shown[index])
        return dlg.CLOSE

    window = dlg.show_list_window(
        parent,
        show_modal,
        title=title,
        purpose=purpose,
        list_label=list_label,
        list_help=list_help,
        rows=rows,
        actions=[dlg.Action("C&hoose", "Use the selected one. Enter does the same.", choose)],
        details=lambda i: details(shown[i]) if i < len(shown) else "",
        filter_label=filter_label,
        filter_help=filter_help,
        on_filter=narrow,
        on_enter=choose,
    )
    window.Destroy()
    return picked[0] if picked else None

"""List Inline Notes: every note in the document, in one window (Alt+Shift+Enter).

Shared by QUILL and QUILL Lite. The idea is PlanCake's (Andre of Oire
Software): a note you can only meet one at a time is a note you cannot review.
Here they are all at once -- what each note says, the line it is on, and the
first sentence of the text it is about -- with an orphaned note (its text was
deleted) listed last as "the text it was on is gone", which is the first place
such a note can be seen and removed.

**Keys.** Enter goes to the selected note and closes the window; Delete
deletes it; F2 edits it; Escape closes. Buttons: Go To, Edit, Delete,
Remove All (asks first, No by default), Copy All and Export (Markdown or
JSON). Close carries no access key (GATE-14).

The window does not do the work itself. The host passes :class:`NotesListHost`
callbacks -- the same code Delete Inline Note and the note dialog use -- and the
list is rebuilt from the document after each one, so it can never show a note
that is not there. Spoken: only outcomes the screen reader cannot see ("Inline
note deleted", "3 notes removed", "Notes copied"); the rows read themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.inline_notes_list import NoteRow

__all__ = ["NotesListHost", "show_inline_notes_list"]

TITLE = "Inline Notes"


@dataclass(slots=True)
class NotesListHost:
    """What the window asks of the editor. Each callback re-reads the document."""

    rows: Callable[[], list[NoteRow]]
    edit: Callable[[NoteRow], None]
    delete: Callable[[NoteRow], bool]
    remove_all: Callable[[], int]
    copy_all: Callable[[list[NoteRow]], None]
    export: Callable[[list[NoteRow]], None]


def show_inline_notes_list(
    wx: Any, parent: Any, show_modal_dialog: Any, host: NotesListHost
) -> NoteRow | None:
    """Show the list. Returns the row to go to, or ``None`` when closed."""
    from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

    chosen: dict[str, NoteRow | None] = {"row": None}
    rows: list[NoteRow] = []
    dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize((760, 460))
    sizer = wx.BoxSizer(wx.VERTICAL)
    label = wx.StaticText(dialog, label="&Notes:")
    sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
    listing = wx.ListCtrl(dialog, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    listing.SetName("Inline notes")
    listing.SetHelpText(
        "Every note in this document, in order: the note, the line it is on, the "
        "text it is about, and whether it is private or written into the file. "
        "Enter goes to the note; Delete deletes it; F2 edits it."
    )
    for index, (heading, width) in enumerate((
        ("Note", 300),
        ("Line", 60),
        ("On", 260),
        ("Kind", 100),
    )):
        listing.InsertColumn(index, heading, width=width)
    sizer.Add(listing, 1, wx.EXPAND | wx.ALL, 10)

    buttons = wx.BoxSizer(wx.HORIZONTAL)

    def _button(text: str, help_text: str, **kwargs: Any) -> Any:
        button = wx.Button(dialog, label=text, **kwargs)
        button.SetHelpText(help_text)
        buttons.Add(button, 0, wx.RIGHT, 6)
        return button

    go_btn = _button("&Go To", "Move to the selected note's text and close this window.")
    edit_btn = _button("&Edit", "Change the selected note's text.")
    delete_btn = _button("&Delete", "Delete the selected note. The document text is kept.")
    remove_btn = _button("&Remove All...", "Delete every note in this document, after asking.")
    copy_btn = _button("Cop&y All", "Copy every note as plain text, one per paragraph.")
    export_btn = _button("E&xport...", "Save every note to a Markdown or JSON file.")
    buttons.AddStretchSpacer()
    close_btn = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close_btn.SetHelpText("Close the list.")
    buttons.Add(close_btn, 0)
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

    def _selected() -> NoteRow | None:
        index = listing.GetFirstSelected()
        return rows[index] if 0 <= index < len(rows) else None

    def _refill(keep: int = 0) -> None:
        rows[:] = host.rows()
        listing.DeleteAllItems()
        for number, row in enumerate(rows):
            listing.InsertItem(number, row.summary(80))
            listing.SetItem(number, 1, "" if row.line is None else str(row.line))
            listing.SetItem(number, 2, row.on_label())
            listing.SetItem(number, 3, row.kind_label())
        has_rows = bool(rows)
        for button in (go_btn, edit_btn, delete_btn, remove_btn, copy_btn, export_btn):
            button.Enable(has_rows)
        if has_rows:
            index = max(0, min(keep, len(rows) - 1))
            listing.Select(index)
            listing.Focus(index)
        else:
            close_btn.SetFocus()

    def _go(_e: Any = None) -> None:
        row = _selected()
        if row is None:
            return
        chosen["row"] = row
        dialog.EndModal(wx.ID_OK)

    def _edit(_e: Any = None) -> None:
        row = _selected()
        if row is not None:
            index = listing.GetFirstSelected()
            host.edit(row)
            _refill(index)

    def _delete(_e: Any = None) -> None:
        row = _selected()
        if row is not None:
            index = listing.GetFirstSelected()
            if host.delete(row):
                _refill(index)

    def _remove_all(_e: Any) -> None:
        if host.remove_all():
            _refill()

    def _on_key(event: Any) -> None:
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            _go()
        elif code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            _delete()
        elif code == wx.WXK_F2:
            _edit()
        else:
            event.Skip()

    go_btn.Bind(wx.EVT_BUTTON, _go)
    edit_btn.Bind(wx.EVT_BUTTON, _edit)
    delete_btn.Bind(wx.EVT_BUTTON, _delete)
    remove_btn.Bind(wx.EVT_BUTTON, _remove_all)
    copy_btn.Bind(wx.EVT_BUTTON, lambda _e: host.copy_all(list(rows)))
    export_btn.Bind(wx.EVT_BUTTON, lambda _e: host.export(list(rows)))
    listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, _go)
    listing.Bind(wx.EVT_KEY_DOWN, _on_key)
    bind_close_button(dialog, close_btn)

    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    _refill()
    wx.CallAfter(listing.SetFocus)
    try:
        show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()
    return chosen["row"]

"""Saved AI Conversations: open an earlier conversation again, or delete one.

QUILL has saved its AI conversations since AI-20: every exchange in Ask Quill is
written to a branchable writing session (:mod:`quill.core.ai.sessions`), and
AI Session Branches reads them back. Since 2026-10-15 the free AI's conversation
window -- shared by QUILL and QUILL Lite (:mod:`quill.ui.hosted_ai_chat`) --
saves into the same store in the same format, through the same recorder
(:func:`~quill.core.ai.sessions.record_exchange`), and this window is how one is
reached again. In QUILL the store is the one Ask Quill uses, so its free-AI
conversations appear in AI Session Branches too; in QUILL Lite it is QUILL
Lite's own data folder.

A plain list, newest first, each row the conversation's first words, how many
messages it holds and when it was last used. Enter opens; Delete asks first.
Every control has its F1 sentence at construction.
"""

from __future__ import annotations

from pathlib import Path

import wx

from quill.core.ai import sessions as store
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

__all__ = ["SavedConversationsDialog", "choose_saved_conversation", "row_label"]

TITLE = "Saved AI Conversations"


def row_label(summary: store.SessionSummary) -> str:
    """One list row: the conversation's first words, its size and its date."""
    messages = "message" if summary.turn_count == 1 else "messages"
    when = (summary.updated_at or "")[:10]
    tail = f", last used {when}" if when else ""
    return f"{summary.title}, {summary.turn_count} {messages}{tail}"


class SavedConversationsDialog(wx.Dialog):
    """The saved conversations in *directory*, newest first."""

    def __init__(self, parent: wx.Window, directory: Path, announce) -> None:  # noqa: ANN001
        super().__init__(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._directory = directory
        self._announce = announce
        self.chosen: store.WritingSession | None = None
        self._rows: list[store.SessionSummary] = []

        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Conversations")
        self._list = wx.ListBox(self, style=wx.LB_SINGLE)
        set_accessible_name(self._list, "Conversations")
        self._list.SetHelpText(
            "Your saved AI conversations, newest first: how each one began, how many "
            "messages it holds and when it was last used. Press Enter to open one."
        )
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._open = wx.Button(self, label="&Open")
        self._open.SetHelpText(
            "Opens the chosen conversation in the conversation window, so you can "
            "read it and carry on where it left off."
        )
        self._delete = wx.Button(self, label="&Delete")
        self._delete.SetHelpText(
            "Deletes the chosen conversation from this computer, after asking. "
            "It cannot be brought back."
        )
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes this window and leaves the conversation you had open.")
        for button in (self._open, self._delete):
            buttons.Add(button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(close, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)

        self._open.Bind(wx.EVT_BUTTON, lambda _e: self._on_open())
        self._delete.Bind(wx.EVT_BUTTON, lambda _e: self._on_delete())
        apply_listbox_activation(self._list, lambda _e: self._on_open())
        bind_close_button(self, close, modeless=False)
        apply_modal_ids(self, escape_id=wx.ID_CANCEL)

        self._refresh()
        self.SetInitialSize(dip_size(self, 560, 420))
        self._list.SetFocus()

    def _refresh(self, keep: int = 0) -> None:
        self._rows = list(store.list_sessions(directory=self._directory))
        self._list.Set([row_label(row) for row in self._rows])
        if self._rows:
            self._list.SetSelection(max(0, min(keep, len(self._rows) - 1)))
        else:
            self._list.Set(["No saved conversations yet."])
            self._list.SetSelection(0)
        self._open.Enable(bool(self._rows))
        self._delete.Enable(bool(self._rows))

    def _current(self) -> store.SessionSummary | None:
        index = self._list.GetSelection()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _on_open(self) -> None:
        summary = self._current()
        if summary is None:
            return
        session = store.load_session(summary.session_id, directory=self._directory)
        if session is None:
            self._announce("That conversation could not be read. Nothing was opened.")
            return
        self.chosen = session
        self.EndModal(wx.ID_OK)

    def _on_delete(self) -> None:
        summary = self._current()
        if summary is None:
            return
        confirm = wx.MessageDialog(
            self,
            f"Delete the conversation “{summary.title}”? It cannot be brought back.",
            "Delete Conversation",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        apply_modal_ids(  # dialog_button_contract: exempt
            confirm, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO
        )
        try:
            agreed = show_modal_dialog(confirm, "Delete Conversation") == wx.ID_YES
        finally:
            confirm.Destroy()
        if not agreed:
            return
        index = self._list.GetSelection()
        store.delete_session(summary.session_id, directory=self._directory)
        self._refresh(keep=index)
        # The list does not announce a row vanishing from under it.
        self._announce("Deleted.")


def choose_saved_conversation(
    parent: wx.Window, directory: Path, announce
) -> store.WritingSession | None:  # noqa: ANN001
    """Show the window; return the conversation chosen to open, or ``None``."""
    dialog = SavedConversationsDialog(parent, directory, announce)
    try:
        show_modal_dialog(dialog, TITLE)
        return dialog.chosen
    finally:
        dialog.Destroy()

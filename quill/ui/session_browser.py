"""Accessible branch browser and compare surface for AI writing sessions (AI-20).

The session-tree engine lives in ``quill.core.ai.sessions`` (wx-free). This
dialog is the screen-reader-operable surface over it: an accessible list of
branches, each announced, with one-key jump (resume) and a compare view that
pages through the turns unique to each branch. No redraw-heavy custom drawing —
plain stock controls (``wx.ListBox`` + read-only ``wx.TextCtrl``).
"""

from __future__ import annotations

from quill.core.ai.sessions import (
    WritingSession,
    branch_rows,
    format_comparison,
    resume,
    save_session,
    summarize_session,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class SessionBrowserDialog:
    def __init__(self, parent: object, session: WritingSession, announce=None) -> None:
        import wx

        self._wx = wx
        self._session = session
        self._announce = announce or (lambda _m: None)
        self._rows = branch_rows(session)

        self.dialog = wx.Dialog(
            parent,
            title="AI Writing Sessions — Branches",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((600, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(self.dialog, label=summarize_session(session))
        summary.Wrap(560)
        root.Add(summary, 0, wx.ALL, 12)

        root.Add(
            wx.StaticText(self.dialog, label="Branches"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            12,
        )
        self.branch_list = wx.ListBox(self.dialog, choices=[row.label for row in self._rows])
        self.branch_list.SetName("Session branches")
        current = next((i for i, row in enumerate(self._rows) if row.is_current), 0)
        if self._rows:
            self.branch_list.SetSelection(current)
        root.Add(self.branch_list, 1, wx.EXPAND | wx.ALL, 12)

        root.Add(
            wx.StaticText(self.dialog, label="Branch details"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            12,
        )
        self.compare_view = wx.TextCtrl(
            self.dialog,
            value=(
                "Select a branch above, then choose Compare with current to see "
                "the turns unique to each branch."
            ),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.compare_view.SetName("Branch details")
        root.Add(self.compare_view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.jump_button = wx.Button(self.dialog, label="Jump to branch")
        self.jump_button.Bind(wx.EVT_BUTTON, self._on_jump)
        buttons.Add(self.jump_button, 0, wx.RIGHT, 8)
        self.compare_button = wx.Button(self.dialog, label="Compare with current")
        self.compare_button.Bind(wx.EVT_BUTTON, self._on_compare)
        buttons.Add(self.compare_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer()
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, label="Close"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)

    def _selected_turn_id(self) -> str | None:
        index = self.branch_list.GetSelection()
        if index < 0 or index >= len(self._rows):
            return None
        return self._rows[index].turn_id

    def _on_jump(self, _event: object) -> None:
        turn_id = self._selected_turn_id()
        if turn_id is None:
            return
        self._session = resume(self._session, turn_id)
        save_session(self._session)
        self._rows = branch_rows(self._session)
        self.branch_list.Set([row.label for row in self._rows])
        # Move focus onto the freshly rebuilt list so screen readers
        # land on the new branch labels (the list itself is the thing
        # that just changed; the announcement names the result but the
        # focus shift is what makes Tab/back-tab work from here).
        self.branch_list.SetFocus()
        self._announce(f"Resumed branch. {summarize_session(self._session)}")

    def _on_compare(self, _event: object) -> None:
        turn_id = self._selected_turn_id()
        current = self._session.current_turn_id
        if turn_id is None or current is None:
            return
        text = format_comparison(self._session, current, turn_id)
        self.compare_view.SetValue(text)
        self._announce("Branch comparison ready.")

    def show(self) -> WritingSession:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        try:
            show_modal_dialog(self.dialog, "AI Writing Sessions — Branches")
        finally:
            self.dialog.Destroy()
        return self._session

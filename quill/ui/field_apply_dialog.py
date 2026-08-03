"""Field-by-field review dialog for structured AI output (5e.38).

One suggestion at a time: the target field, what it currently holds, what the
AI proposes. Accept, Accept and Next, Skip, or Copy — and replacing a field
that already holds something always asks first, defaulting to No. The dialog
never touches the document; the caller applies ``accepted()`` as one
operation when the review closes.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.ai.field_apply import ApplySession, FieldSuggestion
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog


class FieldApplyDialog:
    """Accessible review of :class:`FieldSuggestion` rows against current values."""

    def __init__(
        self,
        parent: object,
        *,
        title: str,
        suggestions: list[FieldSuggestion],
        current_values: dict[str, str],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _message: None)
        self._session = ApplySession(suggestions=list(suggestions))
        self._current_values = dict(current_values)

        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((720, 540))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "Review each suggestion. Accept applies it when you close with "
                "Apply Accepted; Skip leaves the field untouched. Nothing "
                "changes until you apply."
            ),
        )
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self.dialog, label="&Suggestions"), 0, wx.LEFT | wx.RIGHT, 8)
        self.rows = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        set_accessible_name(
            self.rows, "Suggestions - arrows to review, Enter to accept and move on"
        )
        root.Add(self.rows, 1, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self.dialog, label="&Details"), 0, wx.LEFT | wx.RIGHT, 8)
        self.details = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 150),
        )
        set_accessible_name(self.details, "Suggestion details")
        root.Add(self.details, 0, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.accept_next_btn = wx.Button(self.dialog, label="Accept and &Next")
        self.accept_btn = wx.Button(self.dialog, label="&Accept")
        self.skip_btn = wx.Button(self.dialog, label="S&kip")
        self.copy_btn = wx.Button(self.dialog, label="&Copy Value")
        apply_btn = wx.Button(self.dialog, id=wx.ID_OK, label="A&pply Accepted")
        close_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        for button in (self.accept_next_btn, self.accept_btn, self.skip_btn, self.copy_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(apply_btn, 0, wx.RIGHT, 6)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        self.rows.Bind(wx.EVT_LISTBOX, lambda _e: self._show_current())
        self.accept_next_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept(advance=True))
        self.accept_btn.Bind(wx.EVT_BUTTON, lambda _e: self._accept(advance=False))
        self.skip_btn.Bind(wx.EVT_BUTTON, lambda _e: self._skip())
        self.copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._copy())

        self._refresh_rows(select=0)

    # -- data access ---------------------------------------------------

    def accepted(self) -> dict[str, str]:
        return self._session.accepted_values()

    # -- internals -----------------------------------------------------

    def _selected(self) -> int:
        index = self.rows.GetSelection()
        return index if 0 <= index < len(self._session.suggestions) else -1

    def _row_label(self, index: int) -> str:
        status = self._session.statuses[index]
        marker = {"accepted": "accepted", "skipped": "skipped"}.get(status, "")
        suffix = f" ({marker})" if marker else ""
        return f"{self._session.suggestions[index].summary()}{suffix}"

    def _refresh_rows(self, select: int) -> None:
        labels = [self._row_label(i) for i in range(len(self._session.suggestions))]
        self.rows.Set(labels)
        if labels:
            index = max(0, min(select, len(labels) - 1))
            self.rows.SetSelection(index)
            self._show_current()

    def _show_current(self) -> None:
        index = self._selected()
        if index < 0:
            return
        suggestion = self._session.suggestions[index]
        current = self._current_values.get(suggestion.field, "")
        current_text = current if current.strip() else "(empty)"
        self.details.SetValue(
            f"Field: {suggestion.field}\n"
            f"Current value: {current_text}\n"
            f"Suggested value: {suggestion.value}\n"
            f"Status: {self._session.statuses[index]}"
        )

    def _accept(self, *, advance: bool) -> None:
        wx = self._wx
        index = self._selected()
        if index < 0:
            return
        suggestion = self._session.suggestions[index]
        current = self._current_values.get(suggestion.field, "")
        if current.strip() and current.strip() != suggestion.value.strip():
            confirm = wx.MessageDialog(
                self.dialog,
                f'"{suggestion.field}" already contains information. Replace it?',
                "Replace Field?",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            answer = confirm.ShowModal()
            confirm.Destroy()
            if answer != wx.ID_YES:
                self._announce("Kept the current value.")
                return
        self._session.accept(index)
        self._announce(f"Accepted {suggestion.field}.")
        next_index = self._session.next_pending(index) if advance else index
        self._refresh_rows(select=next_index if next_index >= 0 else index)
        if advance and next_index < 0:
            self._announce(f"All suggestions reviewed. {self._session.summary()}")

    def _skip(self) -> None:
        index = self._selected()
        if index < 0:
            return
        self._session.skip(index)
        self._announce(f"Skipped {self._session.suggestions[index].field}.")
        next_index = self._session.next_pending(index)
        self._refresh_rows(select=next_index if next_index >= 0 else index)

    def _copy(self) -> None:
        wx = self._wx
        index = self._selected()
        if index < 0:
            return
        clipboard = wx.TheClipboard
        if clipboard.Open():
            try:
                clipboard.SetData(wx.TextDataObject(self._session.suggestions[index].value))
            finally:
                clipboard.Close()
            self._announce("Suggested value copied to clipboard.")
        else:
            self._announce("Clipboard is unavailable.")

    def show_modal(self) -> int:
        self.dialog.CentreOnParent()
        try:
            return int(show_modal_dialog(self.dialog, self.dialog.GetTitle()))
        finally:
            self.dialog.Destroy()

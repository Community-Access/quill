"""Blame and file history for one repository file (QUILL and QUILL Lite).

Both are a list of runs over a read-only detail: blame runs read "Lines 10 to
14: author, date, short sha, commit title", history rows read "commit title:
author, date, short sha". Alt+N and Alt+P move to the next and previous run from
anywhere in the window, so a listener reading the detail need not go back to
the list first, and Enter on a run opens that commit on GitHub.

The rows are loaded off the UI thread by the caller's *load* callable; a newer
Refresh wins over a slower earlier one through the load token.
"""

from __future__ import annotations

import threading
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

__all__ = ["FileRun", "GitHubFileRunsDialog"]


def _message(exc: BaseException) -> str:
    """The error's sentence, without the support code a screen reader would read out."""
    return str(exc.args[0]) if exc.args else str(exc)


@dataclass(frozen=True, slots=True)
class FileRun:
    """One row: what the list says, what the detail says, and the commit's address."""

    label: str
    detail: str
    url: str = ""


class GitHubFileRunsDialog:
    """A list of blame runs or history commits, with Alt+N/Alt+P and Enter to open."""

    def __init__(
        self,
        parent: object,
        *,
        title: str,
        noun: str,
        load: Callable[[], Sequence[FileRun]],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._title = title
        self._noun = noun
        self._load_rows = load
        self._announce = announce_cb or (lambda _message: None)
        self._rows: list[FileRun] = []
        self._token = 0
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 600, 440))
        self.dialog.SetSize(dip_size(self.dialog, 780, 580))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(panel, label=f"&{noun.capitalize()}")
        list_label.SetHelpText(f"The {noun}, first to last.")
        root.Add(list_label, 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName(title)
        self._list.SetHelpText(
            f"Arrow through the {noun}. Alt+N and Alt+P move to the next and previous one "
            "from anywhere in this window. Enter opens the commit on GitHub."
        )
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        detail_label = wx.StaticText(panel, label="&Details")
        detail_label.SetHelpText("Everything known about the selected row.")
        root.Add(detail_label, 0, wx.LEFT | wx.TOP, 8)
        self._detail = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._detail.SetName("Selected row details")
        self._detail.SetHelpText("Read-only. The commit, its author and date, and its address.")
        root.Add(self._detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="Loading...")
        self._status.SetName(f"{title} status")
        self._status.SetHelpText("Says whether the list is loading, ready, or failed to load.")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._open_btn = wx.Button(panel, label="&Open Commit")
        self._open_btn.SetName("Open the selected commit on GitHub")
        self._open_btn.SetHelpText("Opens the selected row's commit in your browser.")
        self._refresh_btn = wx.Button(panel, label="&Refresh")
        self._refresh_btn.SetName("Load again")
        self._refresh_btn.SetHelpText("Asks GitHub again.")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName(f"Close {title}")
        close_btn.SetHelpText("Close this window.")
        buttons.Add(self._open_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._refresh_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._list.Bind(wx.EVT_LISTBOX, self._on_select)
        apply_listbox_activation(self._list, lambda _event: self._open_commit())
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _event: self._open_commit())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _event: self._load())
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        bind_close_button(self.dialog, close_btn, modeless=False)
        self._open_btn.Enable(False)

    def show(self) -> None:
        wx = self._wx
        self._load()
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, self._title, announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _load(self) -> None:
        self._token += 1
        token = self._token
        self._status.SetLabel("Loading...")
        self._refresh_btn.Enable(False)

        def worker() -> None:
            try:
                rows = list(self._load_rows())
            except Exception as exc:  # noqa: BLE001 - the reason is shown and spoken
                self._wx.CallAfter(self._loaded, token, [], _message(exc))
                return
            self._wx.CallAfter(self._loaded, token, rows, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: blame/history read.

    def _loaded(self, token: int, rows: list[FileRun], error: str) -> None:
        if token != self._token or not dialog_alive(self.dialog):
            return
        self._refresh_btn.Enable(True)
        if error:
            message = f"Could not load the {self._noun}: {error}"
            self._status.SetLabel(message)
            self._announce(message)
            return
        self._rows = rows
        self._list.Set([row.label for row in rows])
        count = len(rows)
        message = f"{count} {self._noun}." if count else f"No {self._noun}."
        self._status.SetLabel(message)
        if rows:
            self._list.SetSelection(0)
            self._on_select(None)
            self._list.SetFocus()
        self._announce(message)

    def _selected(self) -> FileRun | None:
        index = self._list.GetSelection()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _on_select(self, _event: object) -> None:
        row = self._selected()
        self._detail.SetValue(row.detail if row else "")
        self._open_btn.Enable(bool(row and row.url))

    def move(self, step: int) -> None:
        """Alt+N / Alt+P: the next or previous run, said aloud because focus may be elsewhere."""
        if not self._rows:
            self._announce(f"No {self._noun}.")
            return
        index = self._list.GetSelection()
        target = (0 if step > 0 else len(self._rows) - 1) if index < 0 else index + step
        if not 0 <= target < len(self._rows):
            self._announce("Last one." if step > 0 else "First one.")
            return
        self._list.SetSelection(target)
        self._on_select(None)
        if self._wx.Window.FindFocus() is not self._list:
            self._announce(self._rows[target].label)

    def _on_key(self, event: object) -> None:
        wx = self._wx
        if event.GetModifiers() == wx.MOD_ALT and event.GetKeyCode() in (ord("N"), ord("P")):
            self.move(1 if event.GetKeyCode() == ord("N") else -1)
            return
        event.Skip()

    def _open_commit(self) -> None:
        row = self._selected()
        if row is None or not row.url:
            self._announce("This row has no commit to open.")
            return
        self._announce(
            "Opened the commit on GitHub." if webbrowser.open(row.url) else "Could not open it."
        )

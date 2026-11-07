"""An issue's or pull request's timeline as one read-only history to arrow through.

One line per event, oldest first and newest last: labels, assignments, review
requests and reviews, commits, force-pushes, cross-references, closing,
reopening and merging, each with who did it and when. The last line says
whether that is the whole history or only the part QUILL read.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import apply_modal_ids, dialog_alive, show_modal_dialog
from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from quill.core.github.timeline import TimelineResult


class GitHubTimelineDialog:
    """Loads the timeline off the UI thread and shows it as plain text."""

    def __init__(
        self,
        parent: object,
        provider: object,
        repo: str,
        number: int,
        *,
        kind: str = "issue",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._number = number
        self._announce = announce_cb or (lambda _message: None)
        self._title = f"Timeline of {kind} #{number} in {repo}"
        self.dialog = wx.Dialog(
            parent, title=self._title[:120], style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 420))
        self.dialog.SetSize(dip_size(self.dialog, 820, 600))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        history_label = wx.StaticText(panel, label="&History, oldest first:")
        root.Add(history_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._text = wx.TextCtrl(
            panel,
            value="Loading the timeline from GitHub…",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        self._text.SetName("Timeline history")
        self._text.SetHelpText(
            "One line per event with its date and who did it, newest last. "
            "The last line says whether this is the whole history."
        )
        root.Add(self._text, 1, wx.EXPAND | wx.ALL, 10)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(panel, wx.ID_ANY, label="Copy &All")
        self._copy_btn.SetHelpText("Copy the whole history to the clipboard.")
        self._copy_btn.Enable(False)
        close_btn = wx.Button(panel, wx.ID_CANCEL, label="Close")
        close_btn.SetHelpText("Close the timeline.")
        buttons.Add(self._copy_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._copy)

    def _load(self) -> None:
        fetch = getattr(self._provider, "fetch_timeline", None)
        if fetch is None:
            self._failed("This session cannot read timelines.")
            return

        def worker() -> None:
            try:
                result = fetch(self._repo, self._number)
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._failed, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - say it rather than lose it
                self._wx.CallAfter(self._failed, f"Unexpected error: {exc}")
                return
            self._wx.CallAfter(self._ready, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: timeline read.

    def _ready(self, result: TimelineResult) -> None:
        if not dialog_alive(self.dialog):
            return
        self._text.SetValue(result.text())
        self._text.SetInsertionPoint(0)
        self._copy_btn.Enable(True)
        events = len(result.entries)
        self._announce(
            f"Timeline loaded, {events} event{'s' if events != 1 else ''}."
            + ("" if result.complete else " Only part of the history was read.")
        )

    def _failed(self, message: str) -> None:
        if not dialog_alive(self.dialog):
            return
        self._text.SetValue(f"Could not load the timeline. {message}")
        self._announce(f"Could not load the timeline. {message}")

    def _copy(self, _event: object) -> None:
        wx = self._wx
        if not wx.TheClipboard.Open():
            self._announce("Could not open the clipboard.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(self._text.GetValue()))
        finally:
            wx.TheClipboard.Close()
        self._announce("Copied the timeline." if copied else "Could not copy the timeline.")

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
        self._text.SetFocus()
        try:
            show_modal_dialog(self.dialog, "Timeline", announce=self._announce)
        finally:
            self.dialog.Destroy()


__all__ = ["GitHubTimelineDialog"]

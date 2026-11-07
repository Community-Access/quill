"""A read-only "What Failed" window for one workflow run (QUILL and QUILL Lite).

One multi-line text field holding the whole digest, so it reads with the arrow
keys like any document and copies with Ctrl+A, Ctrl+C or the Copy All button.
The digest is built off the UI thread by
:func:`quill.core.github.run_failure_digest.collect_failure_digest`; a newer
Refresh wins over a slower earlier one through the load token.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.run_failure_digest import collect_failure_digest
from quill.core.github.workflow_job_logs import fetch_job_log
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider

__all__ = ["RunFailureDigestDialog"]


class RunFailureDigestDialog:
    """Failed jobs, failed steps, annotations and log tails, as one plain text."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        repo: str,
        run_id: int,
        run_label: str,
        attempt_number: int | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._run_id = run_id
        self._run_label = run_label
        self._attempt = attempt_number
        self._announce = announce_cb or (lambda _message: None)
        self._token = 0
        self.dialog = wx.Dialog(
            parent,
            title=f"What Failed: {run_label}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 640, 460))
        self.dialog.SetSize(dip_size(self.dialog, 820, 620))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(panel, label="&What failed")
        label.SetHelpText("Each failed job, its failed steps, annotations, and log lines.")
        root.Add(label, 0, wx.ALL, 8)
        self._text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.HSCROLL,
        )
        self._text.SetName("What failed in this workflow run")
        self._text.SetHelpText(
            "Read-only. Each failed job, then its failed steps, then annotations with "
            "file and line, then the last 40 log lines of each failed step, with "
            "timestamps and colour codes removed. Arrow through it; Ctrl+A then Ctrl+C copies."
        )
        root.Add(self._text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="Loading what failed...")
        self._status.SetName("What failed status")
        self._status.SetHelpText("Says whether the digest is loading, ready, or failed to load.")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(panel, label="&Copy All")
        self._copy_btn.SetName("Copy the whole digest")
        self._copy_btn.SetHelpText("Copies the whole digest to the clipboard as plain text.")
        self._refresh_btn = wx.Button(panel, label="&Refresh")
        self._refresh_btn.SetName("Load the digest again")
        self._refresh_btn.SetHelpText("Asks GitHub again, for a run that was still finishing.")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close what failed")
        close_btn.SetHelpText("Close this window.")
        buttons.Add(self._copy_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._refresh_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._copy)
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _event: self._load())
        bind_close_button(self.dialog, close_btn, modeless=False)
        self._copy_btn.Enable(False)

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
            show_modal_dialog(self.dialog, "What Failed", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _load(self) -> None:
        self._token += 1
        token = self._token
        self._status.SetLabel("Loading what failed...")
        self._refresh_btn.Enable(False)

        def worker() -> None:
            try:
                text = collect_failure_digest(
                    self._provider,
                    self._repo,
                    self._run_id,
                    self._run_label,
                    attempt_number=self._attempt,
                    fetch_log=fetch_job_log,
                )
            except Exception as exc:  # noqa: BLE001 - listing the jobs failed
                self._wx.CallAfter(self._loaded, token, "", str(exc))
                return
            self._wx.CallAfter(self._loaded, token, text, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: digest fetch.

    def _loaded(self, token: int, text: str, error: str) -> None:
        if token != self._token or not dialog_alive(self.dialog):
            return
        self._refresh_btn.Enable(True)
        if error:
            message = f"Could not load what failed: {error}"
            self._status.SetLabel(message)
            self._announce(message)
            return
        self._text.SetValue(text)
        self._text.SetInsertionPoint(0)
        self._copy_btn.Enable(bool(text))
        lines = text.splitlines()
        summary = lines[1] if len(lines) > 1 else "Ready."
        self._status.SetLabel(summary)
        self._text.SetFocus()
        self._announce(f"What failed is ready. {summary}")

    def _copy(self, _event: object) -> None:
        wx = self._wx
        value = self._text.GetValue()
        if not value:
            return
        if not wx.TheClipboard.Open():
            self._announce("Could not open the clipboard.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(value))
        finally:
            wx.TheClipboard.Close()
        self._announce("Copied what failed." if copied else "Could not copy what failed.")

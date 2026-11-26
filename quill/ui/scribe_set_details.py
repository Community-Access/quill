"""Set Details: one named set of Scribe documents, opened with Enter on the set
in Conversions on This Computer (2026-11-24).

* **Conversion log** -- a read-only multi-line field, focused on open, with
  ``Conversion log.txt`` as it is so far: one line per event, each with its
  time. Arrow through it, or pan it on a braille display. It is read when the
  window opens and again after the person's own Retry Failed or Stop
  Waiting, never under them while they read.
* **Open Folder**, **Retry Failed**, **Stop Waiting** and **Close**. A
  button that has nothing to do says why, in words, rather than being
  greyed out of the Tab order.

Escape closes it, and focus goes back to the set's row.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import wx

from quill.core.batch_sets import BatchSet
from quill.core.scribe import queue as q
from quill.core.scribe import sets
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

#: When the log cannot be read (its folder was moved or deleted).
NO_LOG = "The conversion log could not be read. Its folder may have been moved or deleted."


class ScribeSetDetailsDialog(wx.Dialog):
    def __init__(self, parent: Any, controller: Any, batch_set: BatchSet) -> None:
        super().__init__(
            parent,
            title=f"Set Details: {batch_set.name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.SetName("scribe_set_details_dialog")  # F1 finds its topic by this name
        self._controller = controller
        self._set = batch_set
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="Conversion &log:"), 0, wx.LEFT | wx.TOP, 6)
        self.log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP)
        self.log.SetMinSize(self.FromDIP(wx.Size(560, 260)))
        self.log.SetHelpText(
            "Everything that has happened to this set so far, one line for each event, "
            "each starting with its time. The same text is in Conversion log.txt in the "
            "set's folder."
        )
        sizer.Add(self.log, 1, wx.EXPAND | wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.open_folder = wx.Button(self, label="Open &Folder")
        self.open_folder.SetHelpText("Opens the set's folder: one folder for each document.")
        self.retry = wx.Button(self, label="&Retry Failed")
        self.retry.SetHelpText("Sends every document of the set that was not made again.")
        self.stop = wx.Button(self, label="&Stop Waiting")
        self.stop.SetHelpText(
            "Stops waiting for the documents still to finish. Scribe may still finish any it "
            "had started, and may use pages."
        )
        close = wx.Button(self, wx.ID_CLOSE, label="Close")
        close.SetHelpText("Closes Set Details. The set carries on.")
        for button in (self.open_folder, self.retry, self.stop, close):
            row.Add(button, 0, wx.ALL, 4)
        sizer.Add(row)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self, affirmative_id=wx.ID_CLOSE, cancel_id=wx.ID_CLOSE)
        bind_close_button(self, close, modeless=False)
        self.open_folder.Bind(wx.EVT_BUTTON, lambda _e: self.on_open_folder())
        self.retry.Bind(wx.EVT_BUTTON, lambda _e: self.on_retry())
        self.stop.Bind(wx.EVT_BUTTON, lambda _e: self.on_stop())
        self.reload()
        self.log.SetInsertionPoint(0)
        self.log.SetFocus()

    def reload(self) -> None:
        """The log as it is now, keeping the reading place."""
        try:
            text = self._set.log().read() or ""
        except OSError:
            text = NO_LOG
        place = self.log.GetInsertionPoint()
        self.log.SetValue(text.rstrip("\n") if text else NO_LOG)
        self.log.SetInsertionPoint(min(place, self.log.GetLastPosition()))

    def on_open_folder(self) -> None:
        folder = Path(self._set.folder)
        if folder.is_dir() and hasattr(os, "startfile"):
            os.startfile(str(folder))  # noqa: S606 - the person's own set folder
        elif not folder.is_dir():
            self._controller.host.scribe_announce(f"The folder for {self._set.name} is not there.")

    def on_retry(self) -> None:
        if self._controller.retry_failed(self._set.id):
            self._after_command()

    def on_stop(self) -> None:
        if self._controller.stop_waiting_set(self._set.id):
            self._after_command()

    def _after_command(self) -> None:
        self.reload()
        self.log.SetFocus()


def set_details_text(batch_set: BatchSet, jobs: list[q.Job]) -> str:
    """The Details field of Conversions on This Computer, for a set's row."""
    done, failed, working = sets.set_counts(jobs)
    lines = [sets.set_progress(batch_set, jobs) + "."]
    if working:
        lines.append(f"Still to finish: {working}.")
    not_made = [job.display_name for job in jobs if job.state in q.FINISHED and job.state != q.DONE]
    if not_made:
        lines.append("Not made: " + "; ".join(not_made) + ".")
    lines.append(f"Folder: {batch_set.folder}")
    lines.append("Enter opens Set Details, with the conversion log.")
    return "\n".join(lines)


__all__ = ["NO_LOG", "ScribeSetDetailsDialog", "set_details_text"]

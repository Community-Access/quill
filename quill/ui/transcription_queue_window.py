"""The modeless list of durable file transcriptions on this computer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core.windows_dictation.file_queue import (
    ACTIVE,
    DONE,
    FAILED,
    FINISHED,
    STOPPED,
    TranscriptionJob,
)
from quill.ui import transcription_queue_runtime as queue_runtime
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.dpi import dip_size

TITLE = "Transcriptions on This Computer"
_REFRESH_MS = 1500
_PAD = 8


class TranscriptionsWindow(wx.Dialog):
    """Review, stop, retry and open durable transcription jobs."""

    def __init__(self, parent: Any, host: Any) -> None:
        super().__init__(
            parent,
            title=TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._host = host
        self._jobs: list[TranscriptionJob] = []
        self._ids: list[str] = []
        self._signature: tuple[tuple[object, ...], ...] = ()
        self._cache_owner: Any = None

        self.summary = wx.StaticText(self, label="Loading transcription jobs...")
        self.summary.SetName("Transcription summary")
        jobs_label = wx.StaticText(self, label="&Jobs:")
        self.list = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
        )
        self.list.SetName("Transcription jobs")
        self.list.SetHelpText(
            "Queued, running and finished recordings. Arrow to a job, then use "
            "the buttons below. Enter opens its transcript when one is ready."
        )
        columns = (
            ("Recording", 230),
            ("State", 105),
            ("Progress", 90),
            ("Set", 185),
        )
        for index, (label, width) in enumerate(columns):
            self.list.InsertColumn(index, label, width=self.FromDIP(width))

        details_label = wx.StaticText(self, label="&Details:")
        self.details = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self.details.SetName("Transcription job details")
        self.details.SetHelpText(
            "The selected recording, model, state, progress, set, message and "
            "saved transcript path."
        )
        self.details.SetMinSize(dip_size(self, -1, 115))

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.open_button = self._button(
            row,
            "O&pen Transcript",
            "Opens the finished transcript without changing any document first.",
            self._open,
        )
        self.retry_button = self._button(
            row,
            "Re&try",
            "Queues a failed or stopped recording to run again.",
            self._retry,
        )
        self.stop_button = self._button(
            row,
            "&Stop",
            "Stops the selected queued or running recording.",
            self._stop,
        )
        self.forget_button = self._button(
            row,
            "&Forget",
            "Removes the selected finished job from this computer. It does not "
            "delete a saved transcript.",
            self._forget,
        )
        self.refresh_button = self._button(
            row,
            "Re&load",
            "Reloads the queue from this computer without changing it.",
            self._reload,
        )
        self.close_button = wx.Button(self, wx.ID_CLOSE, label="Close")
        self.close_button.SetHelpText(
            "Closes this window. Queued and running transcription work continues."
        )
        apply_modal_ids(self, cancel_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
        bind_close_button(self, self.close_button, modeless=True)
        row.Add(self.close_button, 0)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(self.summary, 0, wx.EXPAND | wx.ALL, _PAD)
        root.Add(jobs_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(details_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(
            self.details,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM,
            _PAD,
        )
        root.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetInitialSize(dip_size(self, 760, 520))
        self.SetMinSize(dip_size(self, 640, 420))
        self.CentreOnParent()

        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self._sync_selected())
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda _e: self._sync_selected())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._open())
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _e: self._refill(announce=False), self._timer)
        self._refill(announce=False)
        self._timer.Start(_REFRESH_MS)
        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after):
            call_after(self.list.SetFocus)
        else:
            self.list.SetFocus()

    def _button(
        self,
        row: wx.BoxSizer,
        label: str,
        help_text: str,
        action: Any,
    ) -> wx.Button:
        button = wx.Button(self, label=label)
        button.SetHelpText(help_text)
        button.Bind(wx.EVT_BUTTON, lambda _event: action())
        row.Add(button, 0, wx.RIGHT, 6)
        return button

    def _say(self, text: str) -> None:
        say = getattr(self._host, "_dictation_say", None)
        if callable(say):
            say(text)
            return
        voice = getattr(getattr(self._host, "app", None), "voice", None)
        speak = getattr(voice, "speak", None)
        if callable(speak):
            speak(text)

    def _selected_id(self) -> str:
        index = self.list.GetFirstSelected()
        return self._ids[index] if 0 <= index < len(self._ids) else ""

    def _selected(self) -> TranscriptionJob | None:
        wanted = self._selected_id()
        return next((job for job in self._jobs if job.id == wanted), None)

    @staticmethod
    def _row(job: TranscriptionJob) -> tuple[object, ...]:
        progress = (
            f"{round(job.progress * 100)} percent"
            if job.state == "transcribing"
            else ("100 percent" if job.state == DONE else "")
        )
        return (
            job.name,
            job.state_words,
            progress,
            job.batch or "One recording",
            job.id,
            job.message,
        )

    def _refill(self, *, announce: bool) -> None:
        try:
            jobs = sorted(
                queue_runtime.repository_for(self._host).jobs(), key=lambda j: j.created_at
            )
        except OSError as error:
            message = f"The transcription queue could not be read: {error.strerror or error}."
            self.summary.SetLabel(message)
            self.details.SetValue(message)
            if announce:
                self._say(message)
            return
        signature = tuple(self._row(job) for job in jobs)
        if signature != self._signature:
            selected = self._selected_id()
            self.list.DeleteAllItems()
            self._jobs = jobs
            self._ids = [job.id for job in jobs]
            for index, job in enumerate(jobs):
                row = self._row(job)
                item = self.list.InsertItem(index, str(row[0]))
                for column, value in enumerate(row[1:4], start=1):
                    self.list.SetItem(item, column, str(value))
                if job.id == selected:
                    self.list.Select(item, True)
            if not selected and jobs:
                self.list.Select(0, True)
            self._signature = signature
        active = sum(job.state in ACTIVE for job in jobs)
        finished = sum(job.state in FINISHED for job in jobs)
        if not jobs:
            summary = "No transcriptions are queued on this computer."
        else:
            summary = (
                f"{len(jobs)} transcription job{'s' if len(jobs) != 1 else ''}: "
                f"{active} active, {finished} finished."
            )
        self.summary.SetLabel(summary)
        self._sync_selected()
        if announce:
            self._say(summary)

    def _sync_selected(self) -> None:
        job = self._selected()
        if job is None:
            self.details.SetValue("")
            for button in (
                self.open_button,
                self.retry_button,
                self.stop_button,
                self.forget_button,
            ):
                button.Enable(False)
            return
        output = job.output_path or ""
        details = [
            job.name,
            f"State: {job.state_words}",
            f"Model: {job.model or 'Default'}",
            f"Set: {job.batch or 'One recording'}",
            f"Attempts: {job.attempts}",
        ]
        if job.message:
            details.append(f"Message: {job.message}")
        details.append(f"Recording: {job.source_path}")
        if output:
            details.append(f"Transcript: {output}")
        self.details.SetValue("\n".join(details))
        self.open_button.Enable(job.state == DONE and bool(output) and Path(output).is_file())
        self.retry_button.Enable(job.state in {FAILED, STOPPED})
        self.stop_button.Enable(job.state in ACTIVE)
        self.forget_button.Enable(job.state in FINISHED)

    def _open(self) -> None:
        job = self._selected()
        if job is None or not job.output_path:
            return
        path = Path(job.output_path)
        if not path.is_file():
            self._say(f"The transcript for {job.name} is no longer available.")
            return
        from quill.ui.transcription_queue_host import durable_host

        opener = getattr(durable_host(self._host), "_dictation_open_transcript", None)
        if not callable(opener):
            self._say("This app cannot open the transcript here.")
            return
        opener(path)

    def _retry(self) -> None:
        job = self._selected()
        if job is None:
            return
        if queue_runtime.retry(job.id, self._host):
            self._say(f"Queued {job.name} to try again.")
            self._refill(announce=False)
            return
        self._say(f"{job.name} cannot be retried now.")

    def _stop(self) -> None:
        job = self._selected()
        if job is None:
            return
        if queue_runtime.cancel_waiting(job.id, self._host):
            self._say(f"Stopping {job.name}.")
            self._refill(announce=False)
            return
        self._say(f"{job.name} cannot be stopped now.")

    def _forget(self) -> None:
        job = self._selected()
        if job is None:
            return
        if queue_runtime.remove(job.id, self._host):
            self._say(f"Forgot {job.name} from the transcription list.")
            self._refill(announce=False)
            return
        self._say(f"{job.name} is still active and cannot be forgotten.")

    def _reload(self) -> None:
        self._refill(announce=True)

    def _on_close(self, _event: Any) -> None:
        self._stop_timer()
        self._forget_cached_window()
        self.Destroy()

    def _on_destroy(self, event: Any) -> None:
        event.Skip()
        self._stop_timer()
        self._forget_cached_window()

    def _forget_cached_window(self) -> None:
        if self._cache_owner is None:
            return
        found = getattr(self._cache_owner, "_transcriptions_window", None)
        if found is self:
            self._cache_owner._transcriptions_window = None

    def _stop_timer(self) -> None:
        timer = getattr(self, "_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()


def _cache_owner(host: Any) -> Any:
    app = getattr(host, "app", None)
    return app if hasattr(app, "frames") else host


def open_transcriptions(host: Any) -> TranscriptionsWindow:
    """Show the one queue window for this host or its QUILL Lite app."""
    from quill.ui.transcription_queue_host import durable_host

    owner = _cache_owner(host)
    queue_host = durable_host(host)
    found = getattr(owner, "_transcriptions_window", None)
    if found is not None:
        found._host = queue_host
        found.Show()
        found.Raise()
        found.list.SetFocus()
        return found
    app = getattr(host, "app", None)
    window_parent = None
    if hasattr(app, "frames"):
        window_parent = getattr(app, "shell", None)
    elif hasattr(host, "_dictation_parent"):
        window_parent = host._dictation_parent()
    elif isinstance(getattr(host, "frame", None), wx.Window):
        window_parent = host.frame
    elif isinstance(host, wx.Window):
        window_parent = host
    window = TranscriptionsWindow(window_parent, queue_host)
    window._cache_owner = owner
    owner._transcriptions_window = window
    window.Show()
    window.Raise()
    return window


__all__ = ["TITLE", "TranscriptionsWindow", "open_transcriptions"]

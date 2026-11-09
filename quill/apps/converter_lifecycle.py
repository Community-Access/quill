"""Quill Converter's side jobs and its close: preview, File Properties, the shared
background task, and what happens when the window closes.

Split out of :mod:`quill.apps.converter_actions` (GATE-11), which inherits it.
Four rules hold here:

* Only one job runs at a time. A link being read, a single-video download and
  the Auphonic check count as jobs, so Convert waits for them rather than
  starting a second job that Stop could not reach.
* A preview is numbered. Stopping one and starting the next never lets the
  first one's late result play, end or fail the second, and each preview's
  temporary sound file is removed once it is done with.
* File Properties reads the file off the UI thread, so a slow probe of a large
  file on a network drive does not freeze the window.
* Closing the window exits. A running batch is asked about first; on exit the
  batch is stopped (and waited for briefly, so its FFmpeg is ended rather than
  orphaned), the playlist downloads in the temporary folder are removed, and
  the tray icon goes, without which the process stayed resident and swallowed
  every later launch from Explorer.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import wx

#: How long exit waits for a stopped batch to end its FFmpeg, in seconds.
_STOP_WAIT_SECONDS = 10.0


def _off_ui_thread(work: Callable[[], Any], deliver: Callable[[Any, Any], None]) -> None:
    """Run *work* on a worker thread; ``deliver(result, error)`` on the UI thread."""

    def run() -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - delivered and said on the UI thread
            wx.CallAfter(deliver, None, error)
            return
        wx.CallAfter(deliver, result, None)

    threading.Thread(target=run, daemon=True, name="converter-side-job").start()


class ConverterLifecycleMixin:
    """Preview, File Properties, background tasks and close. See the module docstring."""

    # -- preview --------------------------------------------------------------

    def preview(self, *, original: bool) -> None:
        """Play fifteen seconds of the highlighted (or first) file; again stops."""
        if self._previewing:
            self.stop_preview(announce=True)
            return
        source = self._preview_source()
        if source is None:
            self._announce("Add a file to preview first.")
            return
        ffmpeg = self._ffmpeg()
        if ffmpeg is None:
            return
        from quill.core.audio.assemble import render_preview

        spec = self.current_spec()
        if spec.copy_video:
            spec = replace(spec, copy_video=False, filters=())
        what = "the original" if original else "with your settings"
        number = getattr(self, "_preview_number", 0) + 1
        self._preview_number = number
        self._previewing = True
        self._announce(f"Preparing a preview of {source.name}, {what}.")
        out_wav = Path(tempfile.gettempdir()) / (
            f"quill-converter-preview-{os.getpid()}-{number}.wav"
        )

        def work() -> None:
            render_preview(ffmpeg, source, spec, out_wav, original=original)

        def deliver(_result: Any, error: Any) -> None:
            if error is not None:
                _remove_file(out_wav)
                if number == self._preview_number:
                    self._preview_failed(str(error))
                return
            self._play_preview(out_wav, what, number)

        _off_ui_thread(work, deliver)

    def _preview_source(self) -> Path | None:
        from quill.core.audio.assemble import join_inputs

        index = self._list.GetSelection()
        entries = self._entries
        if index != wx.NOT_FOUND and 0 <= index < len(entries):
            entries = [entries[index]]
        files = join_inputs(entries, recurse=self._recurse.GetValue())
        return files[0] if files else None

    def _play_preview(self, wav: Path, what: str, number: int = 0) -> None:
        if not self._previewing or (number and number != self._preview_number):
            _remove_file(wav)  # stopped, or overtaken by a newer preview
            return
        self._preview_wav = wav
        try:
            import winsound

            winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as error:  # noqa: BLE001 - no sound device, or not Windows
            self._preview_failed(f"Could not play the preview: {error}")
            return
        self._announce(f"Playing 15 seconds {what}. Press the same key again to stop.")
        wx.CallLater(16000, self._preview_ended, number)

    def _preview_ended(self, number: int = 0) -> None:
        if number and number != getattr(self, "_preview_number", 0):
            return  # a later preview owns the flag now
        self._previewing = False
        self._forget_preview_file()

    def _preview_failed(self, reason: str) -> None:
        self._previewing = False
        self._forget_preview_file()
        self._announce(f"Preview failed. {reason}", force=True)

    def stop_preview(self, *, announce: bool = False) -> None:
        self._previewing = False
        self._preview_number = getattr(self, "_preview_number", 0) + 1  # orphan any in flight
        try:
            import winsound

            winsound.PlaySound(None, 0)
        except Exception:  # noqa: BLE001 - nothing to stop
            pass
        self._forget_preview_file()
        if announce:
            self._announce("Preview stopped.")

    def _forget_preview_file(self) -> None:
        wav, self._preview_wav = getattr(self, "_preview_wav", None), None
        if wav is not None:
            _remove_file(wav)

    # -- information ----------------------------------------------------------

    def show_properties(self) -> None:
        """File Properties (Alt+Enter) for the highlighted file, read off the UI thread."""
        source = self._preview_source()
        if source is None:
            self._announce("Highlight a file in the queue first.")
            return
        if getattr(self, "_properties_pending", False):
            self._announce("Still reading the file.")
            return
        from quill.core.audio.media_probe import describe, probe
        from quill.core.volume_info import describe_volume

        def work() -> str:
            # The drive comes last: its name, capacity, used and free space,
            # which is what to check before a long conversion (todo item 46).
            return "\n".join(describe(probe(source)) + describe_volume(source))

        def deliver(text: Any, error: Any) -> None:
            from quill.ui.converter_dialogs import show_text

            self._properties_pending = False
            if error is not None:
                self._announce(f"Could not read {source.name}: {error}")
                return
            show_text(self, "File Properties", text)

        self._properties_pending = True
        self._set_status(f"Reading {source.name}.")
        _off_ui_thread(work, deliver)

    # -- background task (for the shared URL-import orchestration) ---------------

    def _run_background_task(
        self,
        label: str,
        work: Any,
        on_success: Any,
        *,
        notify_on_success: bool = False,
        notify_on_error: bool = True,
        notification_category: str = "",
        protect_on_close: bool = False,
        exclusive: bool = False,
    ) -> None:
        """Run ``work(progress)`` off the UI thread; deliver on the UI thread.

        *exclusive* (or *protect_on_close*, which the shared one-video download
        passes) makes the task a job: nothing else starts until it ends.
        """
        del notify_on_success, notify_on_error, notification_category
        exclusive = exclusive or protect_on_close
        if exclusive:
            if self._busy:
                self._announce("A job is already running.")
                return
            self._busy = True
            self._background_label = label
        self._set_status(f"{label} started")

        def progress(message: str, current: int, total: int) -> None:
            wx.CallAfter(self._note_progress, message or label, current, total)

        def worker() -> None:
            try:
                result = work(progress)
            except Exception as error:  # noqa: BLE001 - surfaced on the UI thread
                wx.CallAfter(self._finish_task, label, error, None, on_success, exclusive)
                return
            wx.CallAfter(self._finish_task, label, None, result, on_success, exclusive)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_task(
        self, label: str, error: Any, result: Any, on_success: Any, exclusive: bool = False
    ) -> None:
        if exclusive:
            # Free before on_success, which may start the next job (a download).
            self._busy = False
            self._background_label = ""
        if error is not None:
            self._set_status(f"{label} failed")
            self._show_message_box(f"{label} failed.\n\n{error}", label, wx.ICON_ERROR | wx.OK)
            self._refresh_statusbar()
            return
        self._set_status(f"{label} finished")
        try:
            on_success(result)
        finally:
            self._refresh_statusbar()

    def stop_work(self) -> None:
        if self._cancel is not None:
            self._cancel.cancel()
            self._announce("Stopping.", force=True)
        elif getattr(self, "_background_label", ""):
            self._announce(f"{self._background_label} cannot be stopped; it ends on its own.")

    # -- the window's life ------------------------------------------------------

    def _start_ipc_poll(self) -> None:
        """Poll the hand-over queue, so the Explorer verb on ten selected files --
        ten launches -- ends as ten rows in this one window, not nine lost."""
        self._ipc_timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_ipc_timer, self._ipc_timer)
        self._ipc_timer.Start(600)
        self.frame.Bind(wx.EVT_CLOSE, self._on_converter_close)

    def _on_converter_close(self, event: Any) -> None:
        self.handle_app_close(
            event,
            close_action="ask",  # closing exits; "ask" asks only while a job runs
            protected=bool(self._busy),
            confirm=self._converter_close_confirm,
            shutdown=self._converter_shutdown,
        )

    def _converter_close_confirm(self) -> str | None:
        if not self._busy:
            return "exit"
        what = getattr(self, "_background_label", "") or "A conversion"
        answer = self._show_message_box(
            f"{what} is still running. Stop it and exit?",
            "Exit Quill Converter",
            wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        )
        return "exit" if answer in (wx.YES, wx.ID_YES) else None

    def _converter_shutdown(self) -> None:
        """Teardown before the window closes. Never raises: exit must not block."""
        timer = getattr(self, "_ipc_timer", None)
        if timer is not None:
            with contextlib.suppress(Exception):
                timer.Stop()
        with contextlib.suppress(Exception):
            self.stop_preview()
        cancel = getattr(self, "_cancel", None)
        if cancel is not None:
            cancel.cancel()
        thread = getattr(self, "_work_thread", None)
        if thread is not None and thread.is_alive():
            thread.join(_STOP_WAIT_SECONDS)  # its FFmpeg is ended, not orphaned
        for folder in getattr(self, "_download_folders", []):
            shutil.rmtree(folder, ignore_errors=True)
        self._download_folders = []
        self._remove_tray_icon()

    def _on_ipc_timer(self, _event: object) -> None:
        from quill.core.ipc import drain_open_requests

        requests = drain_open_requests(slot="converter")
        if not requests:
            return
        paths = [request.path for request in requests if request is not None]
        if paths:
            self.add_paths(paths)
        frame = self.frame
        if not frame.IsShown():
            self._restore_from_tray()
        frame.Iconize(False)
        frame.Raise()
        self._list.SetFocus()


def _remove_file(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)

"""Convert from URL in Quill Converter: one video, a whole playlist, or a channel.

Split out of :mod:`quill.apps.converter` (GATE-11). The link is read first,
off the UI thread and without downloading anything
(:func:`quill.core.audio.url_collections.read_link`), so the question comes
before the waiting: a single video goes straight to the shared one-video path
(:mod:`quill.ui.audio_studio.convert_audio_dialog`); a playlist or a channel
opens :class:`~quill.ui.converter_dialogs.ConverterLinkDialog`, which asks how
much of it to take, and then every video's audio lands in the queue, numbered,
tagged as one album, ready for Ctrl+Enter.

The download is a Converter job like any other -- the same progress bar,
status line and tray tooltip, the same Stop (Ctrl+Enter), and failures in the
Conversion Report (Ctrl+R) -- and runs on a worker thread that reports through
``wx.CallAfter``.
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Any

import wx

from quill.core.audio.convert import CancelToken

_TITLE = "Convert from URL"


class ConverterUrlMixin:
    """Convert from URL (Ctrl+U). Mixed into the Converter window."""

    def convert_from_url(self) -> None:
        from quill.core.audio.url_import import looks_like_url
        from quill.ui.audio_studio.convert_audio_dialog import _prompt_for_url

        if getattr(self, "_safe_mode", False):
            self._show_message_box("Converting from a link is unavailable in Safe Mode.", _TITLE)
            return
        if self._busy:
            self._announce("A job is already running.")
            return
        url = _prompt_for_url(self)
        if not url:
            return
        if not looks_like_url(url):
            self._show_message_box(
                "That does not look like a web address. Paste a full http:// or https:// link.",
                _TITLE,
            )
            return
        from quill.core.audio.url_collections import read_link

        self._run_background_task(
            "Reading the link",
            lambda _progress: read_link(url),
            lambda info: self._link_read(url, info),
        )

    def _link_read(self, url: str, info: Any) -> None:
        from quill.ui.audio_studio.convert_audio_dialog import _download_then_convert

        if info.kind == "video":
            _download_then_convert(self, url)
            return
        from quill.ui.converter_dialogs import ask_what_to_download

        choice = ask_what_to_download(self, info)
        if choice is None:
            self._set_status("Convert from URL cancelled.")
            return
        if choice == "video":
            _download_then_convert(self, url)
            return
        self._download_collection(choice)

    def _download_collection(self, choice: Any) -> None:
        from quill.core.audio.url_collections import download_collection
        from quill.core.paths import app_data_dir

        cancel = CancelToken()
        what = "channel" if choice.is_channel else "playlist"
        self._begin_work(f"Downloading the {what} {choice.title}", cancel)
        dest = Path(tempfile.mkdtemp(prefix="quill-url-list-"))
        ffmpeg = self._ffmpeg_quiet()

        def progress(done: int, total: int, fraction: float, title: str) -> None:
            if total:
                text = f"Downloading {min(done + 1, total)} of {total}: {title}"
                wx.CallAfter(self._note_progress, text, int((done + fraction) * 1000), total * 1000)
            else:
                wx.CallAfter(self._note_progress, f"Downloading {done + 1}: {title}", 0, 1)

        def worker() -> None:
            try:
                result = download_collection(
                    choice,
                    dest,
                    archive_dir=app_data_dir() / "converter" / "downloaded",
                    ffmpeg=ffmpeg,
                    progress=progress,
                    cancelled=cancel.is_cancelled,
                )
            except Exception as error:  # noqa: BLE001 - said out loud on the UI thread
                wx.CallAfter(self._collection_failed, str(error))
                return
            wx.CallAfter(self._collection_done, choice, result)

        threading.Thread(target=worker, daemon=True, name="converter-url-list").start()

    def _collection_failed(self, message: str) -> None:
        self._end_work()
        self._set_status(message)
        self._announce(message, force=True)

    def _collection_done(self, choice: Any, result: Any) -> None:
        self._end_work()
        if result.files:
            self.add_paths(result.files, announce=False)
        got = len(result.files)
        noun = "file" if got == 1 else "files"
        if result.stopped:
            summary = f"Stopped. {got} {noun} from {choice.title} are in the queue."
        elif got:
            summary = f"Downloaded {got} {noun} from {choice.title} into the queue."
        else:
            summary = f"Nothing new to download from {choice.title}."
        if result.failed:
            summary += f" {len(result.failed)} could not be downloaded; Ctrl+R lists them."
        elif got:
            summary += " Press Ctrl+Enter to convert."
        self._last_report = "\n".join(
            [f"Download report: {choice.title}", summary, ""]
            + [f"Downloaded: {path.name}" for path in result.files]
            + [f"FAILED: {reason}" for reason in result.failed]
        )
        self._last_output = result.folder
        self._set_status(summary)
        self._announce(summary, force=True)

    def _ffmpeg_quiet(self) -> str | None:
        from quill.core.speech.ffmpeg import find_ffmpeg

        found = find_ffmpeg()
        return str(found) if found else None

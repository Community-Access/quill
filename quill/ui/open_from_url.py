"""Open from URL, one flow for QUILL and QUILL Lite (2026-10-04).

The 2026-10-04 PlanCake design note found four bugs in QUILL's Open from URL,
and this module is the fix for all of them, shared so QUILL Lite gains the same
command rather than a second copy:

* **It asks first.** The user guide promised "QUILL checks with you first,
  naming the host and the expected size"; the code asked for the URL and
  downloaded at once. Now the download stops after the server's headers, the
  question is asked with the host, the file name and the size, and no part of
  the file is read until the answer is Yes.
* **A failure is one plain sentence.** ``download_url`` raises the coded
  ``RemoteTransportError``; the old handler caught only ``HTTPError`` and
  ``URLError``, so a network failure escaped as an unhandled error.
* **It runs on the task manager, with progress.** The download blocked the UI
  thread; now it runs as a background task, with a progress window whose
  Cancel button stops it between chunks.
* **The temp file is removed.** Each editor discards it once the document is
  read or its tab closes, and :func:`quill.io.http_transport.sweep_stale_downloads`
  clears anything a crash left behind.

Each editor supplies ``on_downloaded``: what to do with the file once it is on
disk. The flow owns everything before that.
"""

from __future__ import annotations

import threading
import urllib.parse
from collections.abc import Callable
from typing import Any

import wx

from quill.core.open_sources import consent_question, failure_sentence, format_size, prepare_url
from quill.ui.surface_lifetime import surface_tasks

__all__ = ["NOT_A_LINK", "TITLE", "UrlOpenFlow", "ask_for_url"]

TITLE = "Open from URL"

#: Said when what was typed or pasted is not a web address.
NOT_A_LINK = "That is not a web address that can be opened. It needs to start with http or https."

#: How long a worker waits for the consent question before treating it as No.
_ANSWER_DEADLINE_SECONDS = 600.0


def ask_for_url(parent: Any, initial: str = "https://") -> str | None:
    """The address to open, typed or pasted; ``None`` on Cancel."""
    from quill.ui.dialog_contract import show_modal_dialog

    dialog = wx.TextEntryDialog(
        parent,
        "Web address of the document to open (http or https). A GitHub page "
        "link opens the file behind it.",
        TITLE,
        value=initial,
    )
    try:
        if show_modal_dialog(dialog, TITLE) != wx.ID_OK:
            return None
        return str(dialog.GetValue()).strip()
    finally:
        dialog.Destroy()


class UrlOpenFlow:
    """Download one link after asking, with progress, and hand the file over."""

    def __init__(
        self,
        parent: Any,
        *,
        task_manager: Any,
        announce: Callable[[str], None],
        on_downloaded: Callable[[Any], None],
        ask_yes_no: Callable[[str, str], bool] | None = None,
    ) -> None:
        self._parent = parent
        # Wrapped so a result arriving after the window closed is dropped
        # (and logged) rather than touching a destroyed frame.
        self._task_manager = surface_tasks(task_manager, lambda: self._parent)
        self._announce = announce
        self._on_downloaded = on_downloaded
        self._ask_yes_no = ask_yes_no or self._default_yes_no
        self._cancel = threading.Event()
        self._progress: Any = None
        self._last_percent = -2
        self._host = ""

    # -- start ---------------------------------------------------------- #

    def start(self, raw_url: str) -> bool:
        """Begin the download of *raw_url*. ``False`` when it is not a link."""
        url = prepare_url(raw_url)
        if not url:
            self._announce(NOT_A_LINK)
            return False
        from quill.io import http_transport

        http_transport.sweep_stale_downloads()
        self._host = urllib.parse.urlparse(url).hostname or ""

        def work(**kwargs: Any) -> Any:
            token = kwargs.get("cancellation_token")

            def stopped() -> bool:
                return self._cancel.is_set() or bool(token is not None and token.is_cancelled())

            # Looked up when the task runs, so the one egress call site is
            # always the module's own (and a test can stand in for it).
            return http_transport.download_url(
                url,
                progress=self._on_progress,
                confirm=self._confirm_from_worker,
                should_cancel=stopped,
            )

        self._task_manager.submit(
            "open-from-url",
            work,
            on_success=lambda _op, download: self._finished(download),
            on_failure=lambda _op, error: self._failed(error),
        )
        return True

    # -- the question, asked on the UI thread for the worker -------------- #

    def _confirm_from_worker(self, host: str, filename: str, size: int | None) -> bool:
        """Called on the worker once the headers are in; blocks for the answer."""
        done = threading.Event()
        box = {"answer": False}

        def ask() -> None:
            try:
                box["answer"] = self._confirm_on_ui(host or self._host, filename, size)
            finally:
                done.set()

        wx.CallAfter(ask)
        waited = 0.0
        while not done.wait(0.25):
            waited += 0.25
            if self._cancel.is_set() or waited > _ANSWER_DEADLINE_SECONDS:
                return False
            if not wx.IsMainLoopRunning():
                return False
        return bool(box["answer"])

    def _confirm_on_ui(self, host: str, filename: str, size: int | None) -> bool:
        if not self._ask_yes_no(consent_question(host, filename, size), TITLE):
            self._cancel.set()
            self._announce("Download cancelled.")
            return False
        self._open_progress(host, filename)
        return True

    def _default_yes_no(self, question: str, title: str) -> bool:
        from quill.ui.dialog_contract import show_message_box

        style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION
        return bool(show_message_box(question, title, style, self._parent) == wx.YES)

    # -- progress ------------------------------------------------------- #

    def _open_progress(self, host: str, filename: str) -> None:
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        self._progress = AIProgressDialog(
            self._parent,
            TITLE,
            f"Downloading {filename} from {host}...",
            on_cancel=self._cancel.set,
        )
        self._progress.show()

    def _on_progress(self, written: int, total: int | None) -> None:
        """Worker thread: the dialog marshals its own updates to the UI thread."""
        progress = self._progress
        if progress is None:
            return
        if total:
            percent = int(written * 100 / total)
            if percent == self._last_percent:
                return
            self._last_percent = percent
            sizes = f"{format_size(written)} of {format_size(total)}"
            progress.set_progress(percent, f"Downloaded {sizes}")
        elif written - max(self._last_percent, 0) >= 256 * 1024:
            self._last_percent = written
            progress.set_progress(-1, f"Downloaded {format_size(written)}")

    def _close_progress(self) -> None:
        if self._progress is not None:
            try:
                self._progress.close()
            except RuntimeError:
                pass
            self._progress = None

    # -- the two endings -------------------------------------------------- #

    def _finished(self, download: Any) -> None:
        self._close_progress()
        self._on_downloaded(download)

    def _failed(self, error: BaseException) -> None:
        from quill.io.http_transport import DownloadCancelledError

        self._close_progress()
        if isinstance(error, DownloadCancelledError):
            # A No already said "Download cancelled."; a Cancel part way says it here.
            if "declined" not in str(error):
                self._announce("Download cancelled.")
            return
        self._announce(failure_sentence(error, self._host))

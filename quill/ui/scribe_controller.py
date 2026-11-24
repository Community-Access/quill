"""Scribe for Documents in one app: the shared controller every app uses.

QUILL and QUILL Lite (and later the other apps) each make one
:class:`ScribeController` with a small :class:`ScribeHost` adapter, and get
the whole family integration from it: the availability check (Safe Mode, no
client ID), sign-in, the convert dialog, the family queue's runner, the
Scribe Conversions window, My Scribe Documents, the options and every
sentence. An app adds only its own entry points (PRD goal 5).

**Who speaks** (7.4a): only while this app holds the queue's runner lock.
**Dialogs** open only straight after the person's own command; a background
job that needs the person waits in Scribe Conversions and says so once.
"""

from __future__ import annotations

import logging
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import wx

from quill.core import scribe
from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say
from quill.core.scribe.errors import ScribeError
from quill.core.scribe.options import ScribeOptions, load_options, save_options
from quill.ui.scribe_controller_events import ScribeEventsMixin
from quill.ui.scribe_job_commands import ScribeJobCommands

logger = logging.getLogger(__name__)


class ScribeHost(Protocol):
    """What an app gives the controller."""

    app_name: str

    def scribe_parent(self) -> Any: ...
    def scribe_announce(self, text: str) -> None: ...
    def scribe_in_front(self) -> bool: ...
    def scribe_open_result(self, job: q.Job, format_id: str, path: Path) -> str:
        """Open a finished output where it is used; return what to say
        ("Word is open in QUILL"), or ``""`` when nothing was opened."""
        ...


_INSTANCES: dict[int, ScribeController] = {}


def controller_for(host: Any) -> ScribeController:
    """The one controller for *host* (an app window), made on first use."""
    key = id(host)
    found = _INSTANCES.get(key)
    if found is None:
        found = ScribeController(host)
        _INSTANCES[key] = found
    return found


class ScribeController(ScribeJobCommands, ScribeEventsMixin):
    def __init__(self, host: ScribeHost) -> None:
        self.host = host
        self.app_name = host.app_name
        self._session: Any = None
        self._queue: q.FamilyQueue | None = None
        self._service: Any = None
        self._speaker = say.Speaker()
        self._window: Any = None
        self._last_sentence = ""
        self._chunk_listeners: dict[str, Callable[[str], None]] = {}
        self._said_needs_you: set[tuple[str, str]] = set()
        self._lock = threading.Lock()
        self._tasks: Any = None

    # ------------------------------------------------------------- plumbing

    def options(self) -> ScribeOptions:
        return load_options()

    def save_options(self, options: ScribeOptions) -> None:
        save_options(options)
        self._speaker.speak_stages = options.speak_stages

    def unavailable(self) -> str:
        return scribe.unavailable_reason(self.app_name)

    def check_available(self) -> bool:
        """True when Scribe can be used; otherwise says why, and nothing is queued."""
        reason = self.unavailable()
        if reason:
            self._say(reason)
            return False
        return True

    @property
    def session(self) -> Any:
        if self._session is None:
            from quill.core.scribe.auth import ScribeSession

            self._session = ScribeSession()
        return self._session

    @property
    def queue(self) -> q.FamilyQueue:
        if self._queue is None:
            self._queue = q.FamilyQueue()
        return self._queue

    def client(self) -> Any:
        from quill.core.scribe.client import ScribeClient

        return ScribeClient(self.session, base_url=self.session.base_url)

    def ensure_service(self) -> None:
        """Start this app's queue runner (it runs only while holding the lock)."""
        if self._service is not None or self.unavailable():
            return
        from quill.core.scribe.runner import QueueService

        options = self.options()
        self._speaker.speak_stages = options.speak_stages
        self._service = QueueService(
            self.app_name,
            queue=self.queue,
            client_factory=self.client,
            download_root=lambda: self.options().download_folder,
            listener=lambda kind, job: wx.CallAfter(self._on_event, kind, job),
        )
        self._service.start()
        import atexit

        atexit.register(self.shutdown)  # hand the queue to the next app at once

    def start_if_jobs_waiting(self) -> None:
        """At app start: pick up jobs another app left (7.4, closing an app)."""
        if self.unavailable():
            return
        try:
            if any(job.state not in q.FINISHED for job in self.queue.jobs()):
                self.ensure_service()
        except OSError:
            pass

    def shutdown(self) -> None:
        if self._tasks is not None:
            self._tasks.shutdown(wait=False, cancel_pending=True)
            self._tasks = None
        if self._service is not None:
            self._service.stop()
            self._service = None

    @property
    def holding(self) -> bool:
        return bool(self._service is not None and self._service.holding)

    def wake(self) -> None:
        self.ensure_service()
        if self._service is not None:
            self._service.wake()

    def _say(self, text: str) -> None:
        if text:
            self._last_sentence = text
            self.host.scribe_announce(text)

    # -------------------------------------------------------------- sign-in

    def ensure_signed_in(self) -> bool:
        """Signed in already, or sign in now (the first time any command runs)."""
        if self.session.is_signed_in():
            return True
        return self.sign_in()

    def sign_in(self) -> bool:
        if not self.check_available():
            return False
        from quill.ui.scribe_signin_dialog import ScribeSignInDialog

        dialog = ScribeSignInDialog(self.host.scribe_parent(), self, app_name=self.app_name)
        try:
            from quill.ui.dialog_contract import show_modal_dialog

            result = show_modal_dialog(dialog, "Sign In to Scribe for Documents")
            return bool(result == wx.ID_OK and self.session.is_signed_in())
        finally:
            dialog.Destroy()

    def sign_out(self, done: Callable[[], None] | None = None) -> None:
        if not self.session.is_signed_in():
            self._say(f"You are not signed in to {scribe.PRODUCT_NAME}.")
            return
        waiting = self.queue.waiting_count()
        question = say.sign_out_question(waiting, app_name=self.app_name)
        if question:
            from quill.ui.dialog_contract import show_message_box

            answer = show_message_box(
                question + "\n\nSign out anyway?",
                "Sign Out of Scribe for Documents",
                wx.YES_NO | wx.CANCEL | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self.host.scribe_parent(),
            )
            if answer != wx.YES:
                return
            for job in self.queue.jobs():
                if job.state in q.ACTIVE or job.state in q.NEEDS_PERSON:
                    self.queue.update(job.id, state=q.STOPPED, message="Signed out")

        def signed_out(_result: Any) -> None:
            self._say(f"Signed out of {scribe.PRODUCT_NAME}.")
            if done is not None:
                done()

        self._background(self.session.sign_out, signed_out)

    def open_account_in_browser(self, path: str = "/settings") -> None:
        """Open My Scribe Account, already signed in (``browser_from_oauth``)."""
        if not self.check_available() or not self.ensure_signed_in():
            return
        self._background(
            lambda: self.client().browser_entry_url(path),
            lambda url: webbrowser.open(url),
        )

    def buy_pages(self, purchase_url: str = "") -> None:
        if purchase_url.startswith("https://"):
            webbrowser.open(purchase_url)
            return
        self.open_account_in_browser("/purchase")

    # ------------------------------------------------------ the background

    def _background(
        self,
        work: Callable[[], Any],
        done: Callable[[Any], None],
        failed: Callable[[BaseException], None] | None = None,
    ) -> None:
        """Run *work* on the controller's task pool; *done* or *failed* back on the UI."""
        if self._tasks is None:
            from quill.stability.task_manager import TaskManager

            self._tasks = TaskManager(max_workers=3)
        self._tasks.submit(
            "scribe-request",
            lambda **_kw: work(),
            on_success=lambda _op, result: done(result),
            on_failure=lambda _op, error: (failed or self._failed)(error),
        )

    def _failed(self, error: BaseException) -> None:
        message = error.message if isinstance(error, ScribeError) else str(error)
        self._say(f"{scribe.PRODUCT_NAME}: {message}")

    # ------------------------------------------------------- convert files

    def convert_files(
        self,
        paths: list[Path],
        *,
        app_formats: list[str] | None = None,
        open_as: str = "",
        title: str = "",
        folder: str = "",
    ) -> list[q.Job]:
        """The one convert dialog, with *paths* already chosen; queue on Send.

        *folder* is where the results go, for an app with its own output folder
        rule (Converter, 8.4); otherwise each document gets its folder in the
        download folder (7.6).

        Only the 23 types Scribe takes, up to 500 MB, are offered (3.1): any
        other file is refused here with its sentence, and nothing is sent.
        """
        if not paths or not self.check_available():
            return []
        paths, refused = self._sendable(paths)
        if not paths:
            for sentence in refused:  # no dialog follows, so nothing cuts them off
                self._say(sentence)
            return []
        if not self.ensure_signed_in():
            return []
        from quill.ui.scribe_convert_dialog import ScribeConvertDialog

        options = self.options()
        dialog = ScribeConvertDialog(
            self.host.scribe_parent(),
            self,
            paths=paths,
            formats=options.formats_for(app_formats),
            options=options,
            refused=refused,  # said in the consent text: a dialog opening cuts speech off
        )
        try:
            from quill.ui.dialog_contract import show_modal_dialog

            if show_modal_dialog(dialog, "Convert with Scribe for Documents") != wx.ID_OK:
                return []
            choice = dialog.result()
        finally:
            dialog.Destroy()
        return self.queue_choice(choice, paths=paths, open_as=open_as, title=title, folder=folder)

    def convert_url(self, url: str, *, open_as: str = "") -> list[q.Job]:
        """Convert from a link that points straight at a file (3.1)."""
        if not url or not self.check_available():
            return []
        from quill.core.scribe.inputs import url_refusal

        refused = url_refusal(url)
        if refused:
            self._say(refused)
            return []
        if not self.ensure_signed_in():
            return []
        from quill.ui.scribe_convert_dialog import ScribeConvertDialog

        options = self.options()
        dialog = ScribeConvertDialog(
            self.host.scribe_parent(),
            self,
            url=url,
            formats=options.formats_for(None),
            options=options,
        )
        try:
            from quill.ui.dialog_contract import show_modal_dialog

            if show_modal_dialog(dialog, "Convert with Scribe for Documents") != wx.ID_OK:
                return []
            choice = dialog.result()
        finally:
            dialog.Destroy()
        return self.queue_choice(choice, url=url, open_as=open_as)

    def convert_existing(self, document: Any) -> list[q.Job]:
        """Make formats from a document already in the account: nothing uploaded."""
        if not self.check_available():
            return []
        from quill.ui.scribe_convert_dialog import ScribeConvertDialog

        options = self.options()
        dialog = ScribeConvertDialog(
            self.host.scribe_parent(),
            self,
            existing=document,
            formats=options.formats_for(None),
            options=options,
        )
        try:
            from quill.ui.dialog_contract import show_modal_dialog

            if show_modal_dialog(dialog, "Convert with Scribe for Documents") != wx.ID_OK:
                return []
            choice = dialog.result()
        finally:
            dialog.Destroy()
        return self.queue_choice(choice, existing=document)

    @staticmethod
    def _sendable(paths: list[Path]) -> tuple[list[Path], list[str]]:
        """The *paths* Scribe takes, and a sentence for each it does not (3.1, 11)."""
        from quill.core.scribe.inputs import refusal

        kept: list[Path] = []
        refused: list[str] = []
        for path in paths:
            code, sentence = refusal(path)
            if code:
                refused.append(sentence)
            else:
                kept.append(path)
        return kept, refused

    def queue_choice(
        self,
        choice: Any,
        *,
        paths: list[Path] | None = None,
        url: str = "",
        existing: Any = None,
        open_as: str = "",
        title: str = "",
        folder: str = "",
    ) -> list[q.Job]:
        """Turn the dialog's answer into jobs on the family queue."""
        options = self.options()
        options.last_formats = list(choice.formats)
        if not existing:
            options.first_upload_done = True
        # This app's choices, as what differs from the account defaults (7.3);
        # checking "save as my account defaults" is never remembered.
        options.remember_choice(
            self.app_name,
            choice.settings,
            choice.settings if choice.save_as_defaults else getattr(choice, "base", None),
        )
        self.save_options(options)
        common = {
            "app": self.app_name,
            "formats": list(choice.formats),
            "settings": choice.settings.to_dict(),
            "save_as_defaults": bool(choice.save_as_defaults),
            "open_as": open_as,
            # Scribe's email goes into the account defaults only if changed (F8).
            "defaults_leave_out": []
            if getattr(choice, "email_changed", False)
            else ["notify_when_complete"],
        }
        jobs: list[q.Job] = []
        if existing is not None:
            # Our own name for it when we uploaded it: Scribe's title is read
            # from inside the document and can be a scan's stamp (F6).
            from quill.core.scribe.library import Library

            name = Library().title_for(existing.id) or existing.display_title
            jobs.append(
                q.Job(
                    file_name=name,
                    title=name,
                    document_id=existing.id,
                    reuse=True,
                    **common,
                )
            )
        elif url:
            jobs.append(q.Job(file_name=url.rsplit("/", 1)[-1] or url, source_url=url, **common))
        for path in paths or []:
            size = path.stat().st_size if path.exists() else 0
            jobs.append(
                q.Job(
                    file_name=path.name,
                    source_path=str(path),
                    size=size,
                    title=title or path.stem,
                    folder=folder,
                    **common,
                )
            )
        # Read while it converts (8.1.3): one file with HTML, in an app that can.
        stream = bool(getattr(choice, "stream", False)) and len(jobs) == 1
        stream = stream and "html" in jobs[0].formats
        if stream:
            jobs[0].open_as = "stream"
        self.queue.add(jobs)  # several files: one after another (the approved exception)
        if choice.password and jobs:
            self.ensure_service()
            if self._service is not None:
                self._service._passwords[jobs[0].id] = choice.password  # noqa: SLF001
        self.wake()
        if stream:
            self.host.scribe_stream_started(jobs[0])
        if self._window is not None:
            self._window.refresh()
        return jobs

    # --------------------------------------------------------- the commands

    def open_conversions(self) -> None:
        """Window > Scribe Conversions (modeless)."""
        if not self.check_available():
            return
        self.ensure_service()
        from quill.ui.scribe_conversions_window import ScribeConversionsWindow

        if self._window is None or not self._window:
            self._window = ScribeConversionsWindow(self.host.scribe_parent(), self)
        self._window.show_from(wx.Window.FindFocus())

    def window_closed(self) -> None:
        self._window = None

    def my_documents(self) -> None:
        if not self.check_available() or not self.ensure_signed_in():
            return
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.scribe_documents_dialog import ScribeDocumentsDialog

        dialog = ScribeDocumentsDialog(self.host.scribe_parent(), self)
        try:
            show_modal_dialog(dialog, "My Scribe Documents")
        finally:
            dialog.Destroy()

    def show_options(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.scribe_options_dialog import ScribeOptionsDialog

        dialog = ScribeOptionsDialog(self.host.scribe_parent(), self)
        try:
            if show_modal_dialog(dialog, "Scribe for Documents Options") == wx.ID_OK:
                self.save_options(dialog.result())
        finally:
            dialog.Destroy()

    def about(self) -> str:
        from quill.core.scribe.consent import ABOUT_TEXT

        return ABOUT_TEXT.format(app=self.app_name)

    def current_job(self) -> q.Job | None:
        try:
            jobs = self.queue.jobs()
        except OSError:
            return None
        running = [j for j in jobs if j.state in q.ACTIVE]
        return running[0] if running else None

    def status(self) -> None:
        """Scribe Status: the current job, once."""
        if not self.check_available():
            return
        self._say(say.status_sentence(self.current_job()))

    def repeat_last(self) -> None:
        self.host.scribe_announce(self._last_sentence or f"Nothing from {scribe.PRODUCT_NAME} yet.")


__all__ = ["ScribeController", "ScribeHost", "controller_for"]

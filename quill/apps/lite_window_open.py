"""Opening a large or networked file without freezing the window (F-05).

The prepare half (:mod:`quill.core.lite.open_prepare`) runs on the app's task
manager; the commit half (``DocumentFileMixin._commit_load``) runs here, on the
UI thread, only if the result is still wanted. Four rules:

* **Busy is said, once, and shown.** "Opening big.txt" is announced and put on
  the status bar's message cell; the title says the same. Nothing announces
  progress per chunk -- there are no chunks, and a listener needs one sentence.
* **The document cannot be typed into while it is empty-and-loading.** It is
  read-only until the commit, because a commit would replace whatever was
  typed. That is the one thing that would lose work here.
* **A stale result is dropped.** Each open bumps a generation; closing the
  window invalidates a ``UiLifetimeToken``. A result for an older generation,
  or for a window being destroyed, is never committed -- closing the opening
  window *is* Cancel, and needs no button of its own.
* **Failure leaves the window as it was and asks what next.** Try Again
  re-runs the read; Close closes the empty window. The failure is a box, not a
  status message, for the same reason ``_report_failure`` is: it cost the user
  the thing they asked for.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core.lite.filetypes import is_rich_path
from quill.core.lite.open_prepare import PLAIN, RICH, PreparedDocument
from quill.core.lite.open_prepare import prepare as prepare_document

__all__ = ["DocumentBackgroundOpenMixin", "app_task_manager"]


def app_task_manager(app: Any) -> Any:
    """The app's one task manager, created the first time something needs it.

    Lazily, because most sessions never open a file large enough to need it,
    and a thread pool that is never used still has to be shut down.
    """
    manager = getattr(app, "task_manager", None)
    if manager is None:
        from quill.stability.task_manager import TaskManager

        manager = TaskManager(max_workers=2)
        app.task_manager = manager
    return manager


class DocumentBackgroundOpenMixin:
    """``begin_background_load`` and its two endings. On ``DocumentFrame``."""

    def begin_background_load(self, path: Path) -> None:
        """Start reading *path* off the UI thread; commit it when it arrives."""
        from quill.stability.task_manager import UiLifetimeToken

        path = Path(path)
        mode = RICH if is_rich_path(path.name) else PLAIN
        try:
            self._check_mode_available(mode)
        except Exception as exc:  # noqa: BLE001 - reported exactly as the sync path does
            self._report_failure("Open failed", f"Could not open {path.name}.\n\n{exc}")
            return
        self._open_generation = getattr(self, "_open_generation", 0) + 1
        generation = self._open_generation
        previous = getattr(self, "_open_lifetime", None)
        if previous is not None:
            previous.invalidate()
        self._open_lifetime = UiLifetimeToken()
        self.opening_path = path
        self._set_editable(False)
        message = f"Opening {path.name}"
        # The number still leads, as in every Lite title; _update_title will
        # not skip its next write, because the cached title is cleared here.
        self._last_title = None
        self.SetTitle(f"{self.number}: {message}... - {self._app_display_name()}")
        self._set_status_message(message)
        self._announce(message)
        # Listed in Activity while it runs, and as its outcome after (qc.md F-10).
        from quill.core import activity

        self._open_progress = activity.LOG.begin(
            activity.Progress(
                operation_id=f"lite-open-{generation}", phase="opening", message=message
            )
        )

        def work(**_kwargs: object) -> PreparedDocument:
            return prepare_document(path, mode)

        app_task_manager(self.app).submit(
            "lite-open",
            work,
            on_success=lambda _op, prepared: self._finish_background_load(
                generation, path, prepared
            ),
            on_failure=lambda _op, exc: self._fail_background_load(generation, path, exc),
            ui_lifetime=self._open_lifetime,
        )

    def cancel_background_load(self) -> None:
        """Forget an open in progress. Called as the window closes; idempotent."""
        self._open_generation = getattr(self, "_open_generation", 0) + 1
        token = getattr(self, "_open_lifetime", None)
        if token is not None:
            token.invalidate()
        self.opening_path = None

    def _still_wanted(self, generation: int) -> bool:
        if generation != getattr(self, "_open_generation", 0):
            return False
        if getattr(self.app, "shutting_down", False):
            return False
        try:
            return bool(self) and not self.IsBeingDeleted()
        except RuntimeError:
            return False

    def _finish_background_load(
        self, generation: int, path: Path, prepared: PreparedDocument
    ) -> None:
        if not self._still_wanted(generation):
            return
        self.opening_path = None
        self._set_editable(True)
        self._set_status_message("")
        self._end_open_progress(path, failed=None)
        if self._commit_load(path, prepared):
            self.app.refresh_all_menus()
            try:
                self.control.SetFocus()
            except RuntimeError:
                pass
        else:
            self._update_title()

    def _fail_background_load(self, generation: int, path: Path, exc: BaseException) -> None:
        if not self._still_wanted(generation):
            return
        from quill.ui.dialog_contract import show_message_box

        self.opening_path = None
        self._set_editable(True)
        self._set_status_message("")
        self._end_open_progress(path, failed=exc)
        self._update_title()
        self._cue_error()
        answer = show_message_box(
            f"Could not open {path.name}.\n\n{exc}\n\nTry again?",
            "Open failed",
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_ERROR,
            self,
        )
        if answer == wx.YES:
            self.begin_background_load(path)
        elif self.path is None and not self.modified:
            # The window was made for this file and holds nothing else: an
            # empty window left behind is a stop a listener has to clear.
            self.Close()

    def _end_open_progress(self, path: Path, *, failed: BaseException | None) -> None:
        """Take the open off Activity's in-progress list and keep its outcome."""
        from quill.core import activity
        from quill.ui.outcome_report import keep_outcome

        progress = getattr(self, "_open_progress", None)
        if progress is not None:
            activity.LOG.end(progress.operation_id)
            self._open_progress = None
        if failed is None:
            keep_outcome("Open", f"Opened {path.name}.", object_name=path.name, path=path)
        else:
            keep_outcome(
                "Open",
                f"Could not open {path.name}.",
                object_name=path.name,
                failed=True,
                reason=str(failed),
            )

    # -- small adapters, so the commit and the frame stay in step -------- #

    def _set_editable(self, on: bool) -> None:
        try:
            self.control.SetEditable(on)
        except (AttributeError, RuntimeError):
            pass

    def _cue_error(self) -> None:
        from quill.core.sound_events import SoundEvent

        try:
            self._cue(SoundEvent.ERROR)
        except Exception:  # noqa: BLE001 - a missing tone is not a failure
            pass

    def _app_display_name(self) -> str:
        from quill.core.lite import APP_NAME

        return APP_NAME

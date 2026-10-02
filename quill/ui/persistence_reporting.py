"""Say a failed settings or history save once, with a Retry and an Open Folder.

The UI half of :mod:`quill.core.persistence_outcome` (qc.md F-01). Installed
once per app (:func:`install`); every guarded write anywhere in the process
then reaches the app's Activity window as a result with two next actions:

* **Retry** writes the same thing again, through the same guard;
* **Open Folder** opens the folder in File Explorer with the file selected, so
  a full disk or a read-only folder is something you can see.

Spoken once per file per minute -- a settings file is written on every toggle,
and a full disk would otherwise say the same sentence after every keystroke.
When a later write of the same file succeeds, that is said too ("Settings
saved now."), because a failure the app announced and never took back is a
failure the listener goes on believing in.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core import activity, persistence_outcome
from quill.core.persistence_outcome import WriteOutcome
from quill.ui.activity_window import report_result

#: Seconds before the same file's failure is spoken again.
REPEAT_SECONDS = 60.0


def open_folder_action(path: Path) -> Callable[[], str]:
    """An Open Folder action that selects *path* in File Explorer."""

    def run() -> str:
        import subprocess

        from quill.core.file_manager import reveal_command

        target = path if path.exists() else path.parent
        subprocess.Popen(reveal_command(str(target)))  # noqa: S603 - our own argv
        return f"Opened the folder holding {path.name}."

    return run


class PersistenceReporter:
    """One app's listener: turns write outcomes into Activity results."""

    def __init__(self, host: Any, *, speak: bool = True, call_after: Any = None) -> None:
        self._host = host
        self._speak = speak
        self._call_after = call_after
        self._failing: dict[Path, float] = {}
        self._retrying: set[Path] = set()

    # Called on the writing thread.
    def __call__(self, outcome: WriteOutcome) -> None:
        if outcome.ok and outcome.path not in self._failing:
            return  # the common case: a save that worked, nothing to say
        deliver = self._call_after
        if deliver is None:
            try:
                import wx

                deliver = wx.CallAfter if wx.GetApp() is not None else None
            except Exception:  # noqa: BLE001 - no wx, deliver inline
                deliver = None
        if deliver is None:
            self.handle(outcome)
        else:
            deliver(self.handle, outcome)

    def handle(self, outcome: WriteOutcome) -> None:
        """Record, and say if due. Runs on the UI thread."""
        if outcome.ok:
            if self._failing.pop(outcome.path, None) is None:
                return
            importance = activity.REVIEW if outcome.path in self._retrying else self._importance()
            report_result(
                self._host,
                activity.ActionResult(
                    action="save",
                    object_name=outcome.what,
                    outcome=activity.COMPLETED,
                    summary=f"{_capital(outcome.what)} saved now, after the earlier failure.",
                    importance=importance,
                ),
            )
            return
        now = time.monotonic()
        last = self._failing.get(outcome.path)
        self._failing[outcome.path] = now if last is None else last
        if last is not None and now - last < REPEAT_SECONDS:
            return
        self._failing[outcome.path] = now
        actions: dict[str, Callable[[], str | None]] = {
            activity.OPEN_FOLDER.id: open_folder_action(outcome.path)
        }
        next_actions = [activity.OPEN_FOLDER]
        if outcome.retry is not None:
            actions[activity.RETRY.id] = self._retry_action(outcome)
            next_actions.insert(0, activity.RETRY)
        report_result(
            self._host,
            activity.ActionResult(
                action="save",
                object_name=outcome.what,
                outcome=activity.FAILED,
                summary=(
                    f"{_capital(outcome.what)} could not be saved. "
                    "Your changes stay in use for this session."
                ),
                reason=outcome.reason_sentence,
                next_actions=tuple(next_actions),
                importance=self._importance(),
                details=f"File: {outcome.path}\nReason code: {outcome.reason}",
            ),
            actions,
        )

    def _importance(self) -> str:
        return activity.SPEAK if self._speak else activity.REVIEW

    def _retry_action(self, outcome: WriteOutcome) -> Callable[[], str]:
        def run() -> str:
            retry = outcome.retry
            if retry is None:
                return "There is nothing to retry."
            self._retrying.add(outcome.path)
            try:
                retry()
            except OSError:
                return f"Still could not save {outcome.what}."
            finally:
                self._retrying.discard(outcome.path)
            return f"Saved {outcome.what}."

        return run


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


def install(host: Any, *, speak: bool = True) -> Callable[[], None]:
    """Start reporting this process's guarded writes to *host*. Returns the stop."""
    reporter = PersistenceReporter(host, speak=speak)
    host._persistence_reporter = reporter
    return persistence_outcome.subscribe(reporter)


__all__ = [
    "REPEAT_SECONDS",
    "PersistenceReporter",
    "install",
    "open_folder_action",
]

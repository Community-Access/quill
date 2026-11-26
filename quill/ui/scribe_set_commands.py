"""The commands on a named set of Scribe documents (2026-11-24).

A mixin of :class:`quill.ui.scribe_controller.ScribeController`, kept apart
so each module stays under the 600-line cap (GATE-11). It uses the
controller's queue, host, options, window and ``_say``.

* :meth:`set_root` -- where a set's folder goes: the app's own output folder
  when it has one, else the person's Scribe download folder.
* :meth:`start_set` -- after Send and Convert, the set for the jobs the
  dialog made (each document's folder, the log's first lines).
* Retry Failed, Stop Waiting and Remove from List for a whole set, and
  :meth:`open_set_details`, the Set Details window.

The set's name, folder and log are :mod:`quill.core.batch_sets`, shared
with the other family apps; the Scribe side is :mod:`quill.core.scribe.sets`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.batch_sets import BatchSet
from quill.core.scribe import queue as q
from quill.core.scribe import sets

#: The job states Retry Failed sends again.
RETRYABLE = frozenset({q.FAILED, q.STOPPED, q.NEEDS_SIGNIN, q.GONE})


class ScribeSetCommands:
    """Set commands, on the controller."""

    queue: Any
    host: Any
    app_name: str
    _window: Any

    def set_root(self, folder: str = "") -> Path:
        """The folder a new set's folder is made in."""
        if folder:
            return Path(folder)
        from quill.core.scribe.library import default_download_root

        chosen = self.options().download_folder
        return Path(chosen) if chosen else default_download_root()

    def start_set(self, choice: Any, jobs: list[q.Job]) -> BatchSet | None:
        """The set the dialog named, for *jobs*; ``None`` for one file, or a
        dialog that asked for no name."""
        name = str(getattr(choice, "set_name", "") or "")
        folder = getattr(choice, "set_folder", None)
        if len(jobs) < 2 or not name or folder is None:
            return None
        return sets.start_set(name, Path(folder), jobs, app=self.app_name, now=self.queue.now())

    def set_jobs(self, set_id: str) -> list[q.Job]:
        try:
            return list(self.queue.batch_jobs(set_id))
        except (OSError, TimeoutError):
            return []

    def retry_failed(self, set_id: str) -> int:
        """Send every document of the set that did not finish again; how many."""
        batch_set = self.queue.get_set(set_id)
        if batch_set is None:
            return 0
        failed = [job for job in self.set_jobs(set_id) if job.state in RETRYABLE]
        if not failed:
            self._say(f"Nothing in {batch_set.name} needs trying again.")
            return 0
        if any(j.error_code == "QUILL-SCRIBE-SIGNIN" for j in failed):
            if not self.ensure_signed_in():
                return 0
        sets.log_retry(self.queue, batch_set, failed)
        for job in failed:
            self.retry(job.id)
        count = len(failed)
        self._say(f"Trying {count} document{'' if count == 1 else 's'} of {batch_set.name} again.")
        return count

    def stop_waiting_set(self, set_id: str) -> int:
        """Stop waiting for every document of the set still to finish."""
        batch_set = self.queue.get_set(set_id)
        if batch_set is None:
            return 0
        waiting = [
            job
            for job in self.set_jobs(set_id)
            if job.state in q.ACTIVE or job.state in q.NEEDS_PERSON
        ]
        if not waiting:
            self._say(f"{self.app_name} is not waiting for anything in {batch_set.name}.")
            return 0
        for job in waiting:
            self.queue.update(job.id, state=q.STOPPED, message="Stopped waiting")
        sets.log_stopped(batch_set, waiting, app_name=self.app_name)
        count = len(waiting)
        self._say(
            f"{self.app_name} stopped waiting for {count} document"
            f"{'' if count == 1 else 's'} of {batch_set.name}. Scribe may still finish "
            "any it had started, and they stay in your Scribe account."
        )
        self.wake()  # the runner writes the set's last line
        return count

    def remove_set(self, set_id: str) -> None:
        """Off the list, with its documents; its folder and log stay."""
        self.queue.remove_set(set_id)

    def open_set_details(self, set_id: str, parent: Any) -> None:
        """Set Details: the log so far, Open Folder, Retry Failed, Stop Waiting."""
        batch_set = self.queue.get_set(set_id)
        if batch_set is None:
            return
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.scribe_set_details import ScribeSetDetailsDialog

        dialog = ScribeSetDetailsDialog(parent, self, batch_set)
        try:
            show_modal_dialog(dialog, dialog.GetTitle())
        finally:
            dialog.Destroy()


__all__ = ["RETRYABLE", "ScribeSetCommands"]

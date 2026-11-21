"""What the Scribe queue runner reports, and what is said about it (PRD 7.4a).

A mixin of :class:`quill.ui.scribe_controller.ScribeController`, kept apart so
each module stays under the 600-line cap (GATE-11). It uses the controller's
queue, host, options, speaker, window and ``_say``.

* **One announcer.** Only the app holding the runner lock speaks.
* **Watch-folder jobs are said by the watch folder** (``open_as == "watch"``):
  their outcome is the watch result, said the way every watch result is, so
  the controller says nothing for them and nothing is said twice (8.1.6).
* **The streaming tab** (8.1.3) gets every chunk of its job, and is told when
  the stream has ended and when the job finishes; its completion is part of
  the one result sentence, never a second message.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say

#: Job ``open_as`` values with their own speakers or openers.
WATCH = "watch"
STREAM = "stream"


class ScribeEventsMixin:
    """The runner's events, on the controller."""

    host: Any
    app_name: str
    queue: Any
    holding: bool
    _speaker: Any
    _window: Any
    _chunk_listeners: dict[str, Callable[[str], None]]

    def add_chunk_listener(self, job_id: str, listener: Callable[[str], None]) -> None:
        """Streamed HTML for *job_id* (the read-while-it-converts tab, 8.1.3)."""
        self._chunk_listeners[job_id] = listener

    def add_job_listener(self, job_id: str, listener: Callable[[str, q.Job], None]) -> None:
        """``stream_done``, ``done`` and ``error`` for *job_id*, on the UI thread."""
        listeners: dict[str, Callable[[str, q.Job], None]] = self.__dict__.setdefault(
            "_job_listeners", {}
        )
        listeners[job_id] = listener

    def _tell_job_listener(self, kind: str, job: q.Job) -> None:
        listener = self.__dict__.get("_job_listeners", {}).get(job.id)
        if listener is not None:
            try:
                listener(kind, job)
            except Exception:  # noqa: BLE001 - a closed tab must not stop the queue's speech
                self.__dict__["_job_listeners"].pop(job.id, None)

    def _on_event(self, kind: str, job: q.Job | None) -> None:
        """On the UI thread: refresh the window, then say what 7.4a allows."""
        if kind == "chunk" and job is not None:
            listener = self._chunk_listeners.get(job.id)
            if listener is not None:
                listener(job.message)
            return
        if kind == "stream_done" and job is not None:
            self._tell_job_listener(kind, job)
            return
        if self._window is not None:
            self._window.refresh(job.id if job is not None else "")
        if job is not None and kind in ("done", "error"):
            self._tell_job_listener(kind, job)
        if not self.holding or job is None:
            return
        if job.open_as == WATCH and kind != "closed_while":
            return  # the watch folder says its own results (8.1.6)
        in_front = self.host.scribe_in_front()
        if kind == "started":
            self._say(say.start_sentence(job))
        elif kind == "changed":
            self._say_quietly(self._speaker.on_change(job, app_in_front=in_front))
        elif kind == "done":
            self._finished(job)
            self._batch_finished(job)
        elif kind == "error":
            if job.error_code == "QUILL-SCRIBE-PAGES":
                self._say(say.error_sentence(job, say.pages_sentence(job.message)))
            elif job.error_code in ("QUILL-SCRIBE-NOTDOC", "QUILL-SCRIBE-TOOBIG"):
                self._say(job.message)  # already names Scribe and the file
            else:
                self._say(say.error_sentence(job, job.message))
            self._batch_finished(job)
        elif kind == "needs_you":
            marker = (job.id, job.state)
            if marker not in self._said_needs_you:
                self._said_needs_you.add(marker)
                self._say(say.needs_you_sentence(job, app_name=self.app_name))
        elif kind == "busy" and self._speaker.once(job, "busy"):
            self._say(say.busy_sentence(self.app_name))
        elif kind == "offline" and self._speaker.once(job, "offline"):
            self._say(say.offline_sentence(job, app_name=self.app_name))
        elif kind == "online":
            self._speaker.forget(job.id, "offline")  # recovery is silent
        elif kind == "closed_while":
            titles = [t for t in job.title.split("|") if t]
            if titles:
                from quill.core.scribe.library import default_download_root

                root = self.options().download_folder or str(default_download_root())
                self._say(say.closed_while_sentence(titles, app_name=self.app_name, folder=root))

    def _batch_finished(self, job: q.Job) -> None:
        """After the last file of a batch: what was made and what was not (7.4)."""
        if not job.batch:
            return
        try:
            jobs = self.queue.batch_jobs(job.batch)
        except (OSError, TimeoutError):
            return
        if len(jobs) > 1 and all(j.state in q.FINISHED for j in jobs):
            if self._speaker.once(q.Job(id=job.batch), "batch"):
                self._say(say.batch_sentence(jobs))

    def _say_quietly(self, text: str) -> None:
        if text:
            self._say(text)

    def _finished(self, job: q.Job) -> None:
        """The one result sentence; open the result only where 7.4a allows."""
        options = self.options()
        opened = ""
        mine = job.app == self.app_name
        if mine and job.open_as == STREAM:
            # The streaming tab is already open: say it is complete (8.1.3).
            finished = getattr(self.host, "scribe_stream_finished", None)
            opened = finished(job) if callable(finished) else ""
        elif mine and options.open_results == "yes" and self.host.scribe_in_front():
            opened = self.open_job_result(job, speak=False)
        self._say(
            say.result_sentence(
                job, app_name=self.app_name, opened=opened, offer=options.open_results == "offer"
            )
        )

    def open_job_result(self, job: q.Job, *, speak: bool = True) -> str:
        """Open Result: the first output, in the tool where it is used (section 9)."""
        from quill.core.scribe.model import valid_formats

        for format_id in valid_formats(list(job.outputs)):
            path = Path(job.outputs[format_id])
            if path.exists():
                said = self.host.scribe_open_result(job, format_id, path)
                if speak and said:
                    self._say(said + ".")
                return said
        if speak:
            self._say(f"{job.display_name} has no result to open yet.")
        return ""

    # ---------------------------------------------------------- next steps

    def next_steps(self, job: q.Job) -> list[tuple[str, Callable[[], None]]]:
        """What can be done with *job*'s finished outputs (8.1.7): each a separate
        command the person chooses, offered by the app. Never run on their own."""
        offer = getattr(self.host, "scribe_next_steps", None)
        if not callable(offer):
            return []
        from quill.core.scribe.model import valid_formats

        ready = {
            format_id: Path(job.outputs[format_id])
            for format_id in valid_formats(list(job.outputs))
            if Path(job.outputs[format_id]).exists()
        }
        return list(offer(job, ready)) if ready else []


__all__ = ["STREAM", "WATCH", "ScribeEventsMixin"]

"""Named sets of Scribe documents: the queue's side of :mod:`quill.core.batch_sets`.

Several files chosen in one Convert dialog are one batch (7.4). When the
person names it, the batch is a **set**: a folder inside the usual Scribe
folder, one subfolder per document, and ``Conversion log.txt``. The family
queue keeps the set's record (:meth:`~quill.core.scribe.queue.FamilyQueue.sets`),
so every app shows the same set and the app running the queue writes its
log, whichever app that is after a restart.

* :func:`start_set` -- the record, each document's folder, and the first
  lines of the log (the set, then each document queued), written by the app
  that queued it.
* :func:`note` -- one document's event (uploaded, conversion started,
  finished with its time, or failed with its reason in plain words), written
  only by the app running the queue.
* :func:`finish_ready_sets` -- the last line of each set whose documents
  have all finished, once, however they finished: made, failed, or the
  person stopped waiting.
* :func:`set_progress` and :func:`set_finished_sentence` -- the row's words
  and the one sentence said when the set is done.

No password, token or document text is ever written to the log: names,
times, counts and plain reasons only.

wx-free.
"""

from __future__ import annotations

import logging
from pathlib import Path

from quill.core.batch_sets import (
    BatchSet,
    document_failed_line,
    document_finished_line,
    document_line,
    member_folder_names,
    progress_sentence,
    retry_line,
    set_finished_line,
    set_started_line,
    stopped_line,
)
from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe import queue as q
from quill.core.scribe.model import formats_phrase

logger = logging.getLogger(__name__)

__all__ = [
    "RETRY_HINT",
    "finish_ready_sets",
    "log_retry",
    "log_stopped",
    "note",
    "plain_reason",
    "set_counts",
    "set_finished_sentence",
    "set_progress",
    "start_set",
]

#: How to send the failed documents again, as the log's last line says it.
RETRY_HINT = (
    "To try them again, open Conversions on This Computer, go to the set, "
    "press Enter and choose Retry Failed."
)

#: The events :func:`note` writes, and the word each line starts with.
_EVENTS = {
    "uploaded": "Uploaded",
    "converting": "Conversion started",
    "resumed": "Carrying on after the app was closed",
}


def _append(batch_set: BatchSet, text: str) -> None:
    """A log line; a log that cannot be written never stops a conversion."""
    try:
        batch_set.log().append(text)
    except OSError:
        logger.info("Scribe set log could not be written id=%s", batch_set.id)


def start_set(
    name: str, folder: Path, jobs: list[q.Job], *, app: str, now: float | None = None
) -> BatchSet:
    """The set for *jobs* (not yet queued): each job's folder inside *folder*,
    and the log's first lines. Queue it with ``queue.add(jobs, batch_set=...)``."""
    formats = list(jobs[0].formats) if jobs else []
    made = BatchSet(name=name, folder=str(folder), app=app, formats=formats)
    if now is not None:
        made.started = now  # the queue's clock, which a set's total time is read on
    for job, sub in zip(jobs, member_folder_names(j.display_name for j in jobs), strict=True):
        job.folder = str(folder / sub)
        job.batch = made.id
    made.members = [job.id for job in jobs]
    _append(made, set_started_line(name, len(jobs), formats_phrase(formats)))
    for job in jobs:
        _append(made, document_line("Queued", job.display_name))
    return made


def plain_reason(job: q.Job) -> str:
    """Why *job* did not finish, in plain words: the sentence the person was
    told, never the text of an exception (a file error keeps only its kind)."""
    message = job.message or ""
    if message.startswith("A file could not be read or written"):
        return "a file could not be read or written on this computer"
    if job.state == q.STOPPED:
        return "you stopped waiting for it" if message != "Signed out" else "you signed out"
    if job.state == q.GONE:
        return f"it is no longer in your {PRODUCT_NAME} account"
    return message or "Scribe did not say why"


def note(queue: q.FamilyQueue, job: q.Job, event: str, *, now: float | None = None) -> None:
    """Log *event* for *job* when it is in a set: ``uploaded``, ``converting``,
    ``resumed``, ``done`` or ``failed``."""
    if not job.batch:
        return
    try:
        batch_set = queue.get_set(job.batch)
    except (OSError, TimeoutError):
        return
    if batch_set is None:
        return
    if event == "done":
        took = None
        if job.started_at:
            took = (queue.now() if now is None else now) - job.started_at
        _append(batch_set, document_finished_line(job.display_name, took))
    elif event == "failed":
        _append(batch_set, document_failed_line(job.display_name, plain_reason(job)))
    elif event in _EVENTS:
        _append(batch_set, document_line(_EVENTS[event], job.display_name))


def set_counts(jobs: list[q.Job]) -> tuple[int, int, int]:
    """(made, not made, still working) for a set's jobs."""
    done = sum(1 for job in jobs if job.state == q.DONE)
    failed = sum(1 for job in jobs if job.state in q.FINISHED and job.state != q.DONE)
    return done, failed, len(jobs) - done - failed


def set_progress(batch_set: BatchSet, jobs: list[q.Job]) -> str:
    """``Board packet: 12 of 34 done, 35 percent`` (and ``, 1 failed``)."""
    done, failed, _working = set_counts(jobs)
    return progress_sentence(batch_set.name, done=done, failed=failed, total=len(jobs))


def _members(queue: q.FamilyQueue, batch_set: BatchSet) -> list[q.Job]:
    by_id = {job.id: job for job in queue.jobs()}
    return [by_id[member] for member in batch_set.members if member in by_id]


def finish_ready_sets(queue: q.FamilyQueue) -> list[BatchSet]:
    """Write the last line of every set whose documents have all finished,
    once each (the record's ``finished`` time guards it across apps), and
    return those sets."""
    finished: list[BatchSet] = []
    try:
        open_sets = [made for made in queue.sets() if not made.finished]
    except (OSError, TimeoutError):
        return finished
    for batch_set in open_sets:
        jobs = _members(queue, batch_set)
        if not jobs or any(job.state not in q.FINISHED for job in jobs):
            continue
        now = queue.now()
        try:
            claimed = queue.update_set(
                batch_set.id, only_if=lambda stored: not stored.finished, finished=now
            )
        except (OSError, TimeoutError):
            continue
        if claimed is None:
            continue
        done, _failed, _working = set_counts(jobs)
        _append(
            claimed,
            set_finished_line(
                claimed.name,
                done=done,
                failed_names=[job.display_name for job in jobs if job.state != q.DONE],
                seconds=now - claimed.started,
                retry_hint=RETRY_HINT,
            ),
        )
        finished.append(claimed)
    return finished


def log_retry(queue: q.FamilyQueue, batch_set: BatchSet, jobs: list[q.Job]) -> None:
    """Retry Failed: the set is under way again, and the log says which."""
    if not jobs:
        return
    try:
        queue.update_set(batch_set.id, finished=0.0)
    except (OSError, TimeoutError):
        return
    _append(batch_set, retry_line([job.display_name for job in jobs]))


def log_stopped(batch_set: BatchSet, jobs: list[q.Job], *, app_name: str) -> None:
    if jobs:
        _append(batch_set, stopped_line([job.display_name for job in jobs], app_name))


def set_finished_sentence(batch_set: BatchSet, jobs: list[q.Job]) -> str:
    """The one sentence when a whole set is done (status bar, Notifications,
    and speech when the person chose it)."""
    done, failed, _working = set_counts(jobs)
    total = len(jobs)
    head = f"{PRODUCT_NAME} finished the set {batch_set.name}"
    if not failed:
        return f"{head}: all {total} documents were made."
    if not done:
        return (
            f"{head}: none of the {total} documents were made. "
            "Its log in the set's folder says why."
        )
    return (
        f"{head}: {done} of {total} made, {failed} failed. "
        "Its log says why, and Retry Failed sends them again."
    )

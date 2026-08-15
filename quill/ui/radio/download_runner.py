"""Driving the download queue: one at a time, off the UI thread, resumable.

:mod:`quill.core.radio.download_queue` is the state -- what is waiting, what is
going, what arrived. This is the part that makes it move, and it is deliberately
the only place that knows about threads.

**One transfer at a time, always.** Not a pool. Every source behind this is a
free library run on donations, and four parallel fetches is a worse citizen for
no benefit anybody can hear. It also keeps the promise the queue makes: a
part-finished book is the first N chapters, in order, which is something you can
start listening to.

**The pump is re-entrant-safe by construction.** Each finished item schedules the
next from the UI thread's own callback, so there is never a moment when two
transfers could both believe they are next -- no lock, because there is no
concurrency to guard.

**Closing the window is not cancelling.** Whether outstanding work continues is
a preference; either way it is said out loud, because a queue that silently
keeps running is exactly as surprising as one that silently stops.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from quill.core.radio.download_queue import DownloadQueue, QueueItem


def queue_of(host: Any) -> DownloadQueue:
    """The host's queue, made on first use.

    Lives on the host rather than as a module global so two windows (or a test)
    never share one queue by accident.
    """
    queue = getattr(host, "_download_queue", None)
    if queue is None:
        queue = DownloadQueue()
        host._download_queue = queue
    return queue


def _announce(host: Any, message: str) -> None:
    announce = getattr(host, "_announce", None)
    if callable(announce) and message:
        announce(message)


def _prefs(host: Any):
    from quill.core.paths import app_data_dir
    from quill.core.radio import download_prefs

    cached = getattr(host, "_download_prefs", None)
    if cached is None:
        cached = download_prefs.load(app_data_dir())
        host._download_prefs = cached
    return cached


def destination_for(host: Any, station: Any, *, work: str = "", author: str = "") -> Path:
    """Where this download belongs, under the listener's own filing rules."""
    from quill.core.radio import download_prefs

    prefs = _prefs(host)
    return download_prefs.plan_destination(
        prefs,
        source=str(getattr(station, "source", "")),
        work=work,
        author=author,
        existing_authors=_authors_on_disk(prefs),
    )


def _authors_on_disk(prefs: Any) -> dict[str, int]:
    """How many works each author already has filed.

    Read from the folder itself rather than a database: the folder *is* the
    record, somebody may have moved things by hand, and a count that disagrees
    with the disk would file the second book somewhere the first is not.
    """
    from quill.core.radio import download_prefs as dp

    books = dp.resolved_root(prefs) / dp.FOLDER_BOOKS
    counts: dict[str, int] = {}
    try:
        for entry in books.iterdir():
            if entry.is_dir():
                counts[entry.name] = sum(1 for child in entry.iterdir() if child.is_dir()) or 1
    except OSError:
        return {}
    return counts


def enqueue(
    host: Any,
    stations: list[Any],
    *,
    group: str = "",
    author: str = "",
) -> int:
    """Add downloadable rows to the queue and start it if it is idle.

    Anything the rights rule refuses is left out here rather than queued and
    failed later -- a queue full of rows that were never going to work is a
    queue nobody trusts.
    """
    from quill.core.radio import downloadable

    savable = [row for row in stations if downloadable.can_download(row)]
    if not savable:
        _announce(host, "There is nothing here that Quill Radio can save.")
        return 0

    # "Ask where to put each download": asked once per batch, not per chapter
    # -- a book is a folder, not forty prompts. Cancelling the prompt cancels
    # the enqueue, said out loud, because a download that silently fell back to
    # the automatic filing after you declined to choose is filing you refused.
    chosen_folder = ""
    if bool(getattr(_prefs(host), "always_ask", False)):
        from quill.ui.radio import download_command

        what = group or f"{len(savable)} file{'' if len(savable) == 1 else 's'}"
        chosen_folder = download_command._choose_folder(host, f"Save {what} to")
        if not chosen_folder:
            _announce(host, "Download cancelled. Nothing was queued.")
            return 0

    queue = queue_of(host)
    was_idle = queue.running is None
    for station in savable:
        queue.add(
            station,
            chosen_folder or destination_for(host, station, work=group, author=author),
            group=group,
        )
    count = len(savable)
    label = group or ("1 file" if count == 1 else f"{count} files")
    _announce(
        host,
        f"Queued {label}. {queue.summary()} You can carry on listening.",
    )
    if was_idle:
        pump(host)
    return count


def pump(host: Any) -> bool:
    """Start the next waiting item, if nothing is already going. True if started."""
    from quill.core.radio import media_download

    queue = queue_of(host)
    if queue.running is not None:
        return False
    item = queue.next_waiting()
    if item is None:
        _on_queue_drained(host, queue)
        return False

    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        queue.fail(item, "downloading is not available here")
        return False

    queue.start(item)
    cancel = threading.Event()
    host._download_cancel = cancel
    _refresh(host)

    def _work(**_kwargs: object) -> Path:
        return media_download.download_one(item.station, item.folder, cancel=cancel)

    def _ok(_op: str, path: Path) -> None:
        queue.finish(item, path)
        _after(host, queue, item)

    def _failed(_op: str, error: BaseException) -> None:
        # A cancel arrives here as a DownloadError; recording it as a failure
        # would tell somebody their download broke when they stopped it.
        if cancel.is_set():
            queue.cancel(item)
        else:
            queue.fail(item, str(error))
        _after(host, queue, item)

    task_manager.submit("radio-download-queue", _work, on_success=_ok, on_failure=_failed)
    return True


def _after(host: Any, queue: DownloadQueue, item: QueueItem) -> None:
    """One item finished: refresh, then start the next."""
    _refresh(host)
    if item.state == "failed":
        # Named as it happens rather than only in the end-of-queue summary: one
        # chapter failing in a forty-chapter book is worth hearing about while
        # there is still something to do about it.
        _announce(host, f"{item.name} could not be downloaded.")
    pump(host)


def _on_queue_drained(host: Any, queue: DownloadQueue) -> None:
    """Everything that was going to happen has happened."""
    if not queue.items:
        return
    if getattr(host, "_download_summary_said", None) == len(queue.items):
        return
    host._download_summary_said = len(queue.items)
    _announce(host, queue.summary())


def _refresh(host: Any) -> None:
    """Tell an open monitor window that something changed."""
    monitor = getattr(host, "_download_monitor", None)
    refresh = getattr(monitor, "refresh", None)
    if callable(refresh):
        refresh()


def cancel_current(host: Any) -> bool:
    """Stop whatever is transferring now. What arrived is kept."""
    cancel = getattr(host, "_download_cancel", None)
    if cancel is None or cancel.is_set():
        return False
    cancel.set()
    return True


def cancel_item(host: Any, item: QueueItem) -> bool:
    """Cancel one row, whether it is waiting or running."""
    queue = queue_of(host)
    if item.state == "running":
        cancel_current(host)
        return True
    return queue.cancel(item)


def clear_all(host: Any) -> int:
    """Empty the queue, stopping anything in flight."""
    cancel_current(host)
    removed = queue_of(host).clear_all()
    host._download_summary_said = None
    _refresh(host)
    return removed


def on_window_closing(host: Any) -> str:
    """What happens to outstanding downloads when the window goes away.

    Returns the sentence to say, which is never empty when there is work
    outstanding: whichever way the preference is set, being told is the point.
    """
    queue = queue_of(host)
    if not queue.outstanding:
        return ""
    keep_going = bool(getattr(_prefs(host), "keep_going_in_background", True))
    if not keep_going:
        cancel_current(host)
        for item in queue.items:
            if item.state == "waiting":
                queue.cancel(item)
    return queue.closing_message(keep_going=keep_going)

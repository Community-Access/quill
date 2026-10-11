"""Checking many feeds: a bounded number at once, one stop for all, milestones once (F-09).

Before this, "check every feed" handed the task manager one job per podcast at
once. With 1,500 podcasts that is 1,500 jobs queued ahead of everything else the
app wants a worker for -- a search, a transcript, a chapter fetch -- so the
first thing a large library's refresh did was make the rest of the app wait,
and nothing could stop it short of quitting.

:class:`FeedRefreshBatch` is the queue in front of that:

* **A concurrency limit.** At most :data:`MAX_IN_FLIGHT` feeds are being
  fetched at any moment; the next starts when one answers. The pool keeps a
  worker free for whatever the listener asks for meanwhile.
* **One cancel for the whole check.** :meth:`~FeedRefreshBatch.cancel` starts
  nothing more and tells the fetches in flight to stop at their next read
  (``feed_reader`` checks between chunks).
* **A per-feed deadline** -- :data:`FEED_DEADLINE_SECONDS` -- is passed to every
  fetch, so one server dribbling bytes cannot hold a slot for ever.
* **Progress once per milestone.** The quarter points of a check of
  :data:`MILESTONE_MIN_FEEDS` or more, and the end -- never a sentence per feed.
* **No duplicates.** :meth:`~FeedRefreshBatch.extend` adds only podcasts not
  already waiting or in flight, so a timer tick during a manual check does not
  fetch the same feed twice.

wx-free; the UI half (which starts each fetch and speaks the milestones) is
``quill/ui/podcasts/feed_refresh.py``. Every method is called on one thread --
the UI thread -- because each fetch reports back through ``wx.CallAfter``; the
lock is there so a test or a future caller on another thread is still safe.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable, Iterable

__all__ = [
    "FEED_DEADLINE_SECONDS",
    "MAX_IN_FLIGHT",
    "MILESTONE_MIN_FEEDS",
    "FeedRefreshBatch",
    "finished_sentence",
    "milestone_sentence",
]

#: Feeds fetched at once. The shared task manager has four workers; three for
#: feeds leaves one for everything else.
MAX_IN_FLIGHT = 3

#: The longest one feed may take, from the first byte requested to the last
#: read, retries included. A healthy feed takes a second or two.
FEED_DEADLINE_SECONDS = 60.0

#: A check this size or larger says where it is at each quarter; a smaller one
#: is over before a progress sentence would help.
MILESTONE_MIN_FEEDS = 20


def _plural(count: int, noun: str) -> str:
    return f"{count:,} {noun}{'' if count == 1 else 's'}"


def milestone_sentence(done: int, total: int, failed: int) -> str:
    """ "Checked 50 of 200 feeds." (and how many failed, when any did)."""
    text = f"Checked {done:,} of {_plural(total, 'feed')}."
    if failed:
        text += f" {failed:,} failed."
    return text


def finished_sentence(done: int, total: int, failed: int, *, cancelled: bool) -> str:
    """The one sentence a manual check ends with."""
    if cancelled:
        return f"Stopped checking feeds. {done:,} of {_plural(total, 'feed')} were checked."
    text = f"Finished checking {_plural(total, 'feed')}."
    if failed:
        text += f" {failed:,} failed; Feed Check lists them."
    return text


class FeedRefreshBatch:
    """A queue of podcasts to check, run :data:`MAX_IN_FLIGHT` at a time."""

    def __init__(
        self,
        *,
        start: Callable[[str, FeedRefreshBatch], None],
        limit: int = MAX_IN_FLIGHT,
        on_milestone: Callable[[str], None] | None = None,
        on_finished: Callable[[FeedRefreshBatch], None] | None = None,
        milestone_min: int = MILESTONE_MIN_FEEDS,
    ) -> None:
        self._start = start
        self._limit = max(1, limit)
        self._on_milestone = on_milestone
        self._on_finished = on_finished
        self._milestone_min = milestone_min
        self._waiting: deque[str] = deque()
        self._queued: set[str] = set()
        self._in_flight: set[str] = set()
        self._accepted: set[str] = set()
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._spoken: set[int] = set()
        self.total = 0
        self.done = 0
        self.failed = 0
        self.new_episodes = 0
        #: The most fetches that were ever in flight together (the limit's proof).
        self.peak_in_flight = 0
        self.finished = False
        #: Whether milestones and the end are spoken: a check somebody asked for.
        self.speak_progress = False
        #: True while :meth:`_fill` is starting fetches, so a fetch that answers
        #: synchronously does not recurse into another fill (a test's fake, or a
        #: start that fails at once, would otherwise nest one frame per feed).
        self._filling = False

    # -- state ---------------------------------------------------------------- #

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def is_cancelled(self) -> bool:
        """For a fetch to ask between reads: has the whole check been stopped?"""
        return self._cancel.is_set()

    @property
    def in_flight(self) -> int:
        with self._lock:
            return len(self._in_flight)

    @property
    def waiting(self) -> int:
        with self._lock:
            return len(self._waiting)

    @property
    def running(self) -> bool:
        return not self.finished

    def describe(self) -> str:
        """Where the check is, for somebody who asks while it runs."""
        return milestone_sentence(self.done, self.total, self.failed)

    # -- driving it ------------------------------------------------------------ #

    def extend(self, show_ids: Iterable[str]) -> int:
        """Queue podcasts not already waiting or in flight. Returns how many were added."""
        added = 0
        with self._lock:
            if self.finished or self.cancelled:
                return 0
            for show_id in show_ids:
                key = str(show_id)
                if key in self._accepted:
                    continue
                self._accepted.add(key)
                self._queued.add(key)
                self._waiting.append(key)
                added += 1
            self.total += added
        self._fill()
        return added

    def _fill(self) -> None:
        with self._lock:
            if self._filling:
                return
            self._filling = True
        try:
            while True:
                with self._lock:
                    if self.cancelled or len(self._in_flight) >= self._limit or not self._waiting:
                        break
                    show_id = self._waiting.popleft()
                    self._queued.discard(show_id)
                    self._in_flight.add(show_id)
                    self.peak_in_flight = max(self.peak_in_flight, len(self._in_flight))
                try:
                    self._start(show_id, self)
                except Exception:  # noqa: BLE001 - one feed that cannot start never stops the rest
                    self.report(show_id, ok=False)
        finally:
            with self._lock:
                self._filling = False
        self._maybe_finish()

    def report(
        self, show_id: str, *, ok: bool, new_episodes: int = 0, stopped: bool = False
    ) -> None:
        """One feed has answered, or failed, or (*stopped*) was cancelled. Starts the next."""
        with self._lock:
            key = str(show_id)
            if key not in self._in_flight:
                return  # not ours, or reported twice
            self._in_flight.discard(key)
            if stopped:
                milestone = False
            else:
                self.done += 1
                if not ok:
                    self.failed += 1
                self.new_episodes += max(0, new_episodes)
                milestone = self._milestone_due()
        if milestone and self._on_milestone is not None:
            self._on_milestone(milestone_sentence(self.done, self.total, self.failed))
        self._fill()

    def _milestone_due(self) -> bool:
        if self.total < self._milestone_min or self.done >= self.total:
            return False
        quarter = self.done * 4 // self.total
        if quarter <= 0 or quarter in self._spoken:
            return False
        self._spoken.add(quarter)
        return True

    def cancel(self) -> bool:
        """Stop the whole check: nothing more starts, fetches in flight are told to stop.

        Returns whether there was anything to stop.
        """
        with self._lock:
            if self.finished or self.cancelled:
                return False
            self._cancel.set()
            self._waiting.clear()
            self._queued.clear()
        self._maybe_finish()
        return True

    def _maybe_finish(self) -> None:
        with self._lock:
            if self.finished or self._in_flight or (self._waiting and not self.cancelled):
                return
            self.finished = True
        if self._on_finished is not None:
            self._on_finished(self)

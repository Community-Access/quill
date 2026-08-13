"""Persisting the podcast library, at any size (QUILL Cast 1.1.0).

One method, ``_save_podcast_library``, is called from everywhere: a position
checkpoint on every pause, a finished download, a mark-as-played, every
folder and favourite action, and every dialog that changes anything. For a
normal library that is free.

It stops being free at scale. Measured against a real 1,307-feed OPML export
once every show has been refreshed -- about 196,000 episodes -- one full
write serializes to a 164 MB JSON document and takes roughly seven seconds.
Running that inside a pause would freeze the window for seconds, every time.

So above a threshold the write coalesces onto a short timer, and below it
nothing changes at all: the save stays inline and immediately durable, exactly
as it always was. The shutdown path always forces a final flush, so the worst
case is losing a few seconds of resume position to a hard kill -- a far better
trade than a seven-second stall on every pause.

(The same shape as the bug that got Earshot force-quit by iOS: per-save work
that grows with the library until it exceeds the save cadence.)
"""

from __future__ import annotations

from quill.core.paths import app_data_dir
from quill.core.podcasts.subscriptions import save_library

#: Above this many episodes, writes coalesce. See the module docstring.
COALESCE_SAVE_ABOVE_EPISODES = 20_000
COALESCE_SAVE_DELAY_MS = 4000


class PodcastLibrarySaveMixin:
    """Coalescing library persistence."""

    def _podcast_library_is_large(self) -> bool:
        """Whether this library is big enough that saves must be coalesced.

        Counted rather than cached: the count is a sum over shows (about a
        thousand additions for a very large library), which is nothing beside
        the write it is deciding about, and a cache would go stale exactly
        when a refresh has just made the library bigger.
        """
        total = sum(len(show.episodes) for show in self._podcast_library.shows)
        return total > COALESCE_SAVE_ABOVE_EPISODES

    def _save_podcast_library(self) -> None:
        """Persist the library -- inline normally, coalesced when it is huge.

        See :data:`COALESCE_SAVE_ABOVE_EPISODES` for why the second mode
        exists and what it costs.
        """
        if self._podcast_library_is_large():
            self._podcast_library_dirty = True
            self._schedule_podcast_library_flush()
        else:
            self._flush_podcast_library()
        settings = self._podcast_library.settings
        self._podcast_download_queue.set_reconnect_settings(
            enabled=settings.reconnect_enabled,
            max_attempts=settings.reconnect_max_attempts,
            wait_seconds=settings.reconnect_wait_seconds,
        )

    def _schedule_podcast_library_flush(self) -> None:
        """Start (or leave running) the coalescing timer."""
        timer = getattr(self, "_podcast_save_timer", None)
        if timer is None:
            timer = self._wx.Timer(self.frame)
            self.frame.Bind(self._wx.EVT_TIMER, self._on_podcast_save_timer, timer)
            self._podcast_save_timer = timer
        if not timer.IsRunning():
            timer.Start(COALESCE_SAVE_DELAY_MS, oneShot=True)

    def _on_podcast_save_timer(self, event: object) -> None:
        timer = getattr(self, "_podcast_save_timer", None)
        if timer is not None and event.GetId() != timer.GetId():
            event.Skip()
            return
        self._flush_podcast_library()

    def _flush_podcast_library(self) -> None:
        """Write the library out now, cancelling any pending coalesced write.

        Safe to call unconditionally -- the shutdown path does exactly that,
        because it cannot know whether the timer got there first and a
        redundant atomic write is cheaper than reasoning about it.
        """
        self._podcast_library_dirty = False
        timer = getattr(self, "_podcast_save_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()
        save_library(app_data_dir(), self._podcast_library)

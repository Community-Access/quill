"""The adaptive cushion: a stream that keeps running dry refills deeper.

When a stream underruns -- the server delivers slower than the audio plays,
so mpv runs out and pauses itself to rebuffer -- mpv starts again as soon as
it has one second buffered (``cache-pause-wait``, default 1). On a stream that
is only slightly too slow, that turns into a stutter every few seconds: one
second in, one second out, forever.

The answer, and the numbers, come from BlindRadio by serrebidev (MIT),
``CHANGELOG.md`` 0.2.2 and ``crates/blindradio-core/src/stream.rs``: after a
stream runs dry it must refill a deeper cushion before it sounds again --
three seconds, then nine, up to fifteen -- so playback comes back in long
stretches between clean gaps. A clean minute earns the normal cushion back,
changing station resets it, and a stream that never runs dry behaves exactly
as before. No code is copied.

In mpv the cushion is ``cache-pause-wait``: how many seconds the cache must
hold before playback resumes after "buffering". mpv's player loop reads it on
every update (``player/playloop.c``), so writing the property takes effect on
the very next stall, without reloading the stream. (``cache-secs`` and
``demuxer-readahead-secs`` limit how far ahead mpv reads; with the cache on,
Quill Radio already reads as far ahead as the buffer's byte cap allows, so a
larger read-ahead would change nothing here.)

This module is the policy only: which cushion, when. It has a clock rather
than a timer, so a fake clock drives every case in the tests. wx-free and
strict-typed; :mod:`quill.ui.radio.mpv_live_extras` applies what it decides.
"""

from __future__ import annotations

import time
from collections.abc import Callable

#: mpv's own ``cache-pause-wait`` default: what a stream that never runs dry
#: keeps.
NORMAL_SECONDS = 1.0

#: The deeper cushions, one step per underrun (BlindRadio: 3, then 9, up to 15).
STEPS: tuple[float, ...] = (3.0, 9.0, 15.0)

#: How long playback must run without a stall to earn the normal cushion back.
CLEAN_SECONDS = 60.0


class CushionPolicy:
    """Decides the refill cushion for the stream that is playing.

    Every method returns the cushion to apply when it *changed*, or ``None``
    when it did not, so the caller writes to mpv only when there is news.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._step = -1
        self._stalled = False
        #: When playback last came back from a stall; the clean minute counts
        #: from here, because a stall that is still going on is not clean.
        self._clean_since: float | None = None

    @property
    def seconds(self) -> float:
        """The cushion now in force."""
        return NORMAL_SECONDS if self._step < 0 else STEPS[self._step]

    @property
    def raised(self) -> bool:
        return self._step >= 0

    def stall_started(self) -> float | None:
        """The stream ran dry: go one step deeper (up to the last)."""
        self._stalled = True
        self._clean_since = None
        if self._step >= len(STEPS) - 1:
            return None
        self._step += 1
        return self.seconds

    def stall_ended(self) -> None:
        """Playback is back; the clean minute starts now."""
        self._stalled = False
        self._clean_since = self._clock()

    def tick(self) -> float | None:
        """Called while playing. Returns the normal cushion once a minute is clean."""
        if self._step < 0 or self._stalled or self._clean_since is None:
            return None
        if self._clock() - self._clean_since < CLEAN_SECONDS:
            return None
        self._step = -1
        self._clean_since = None
        return NORMAL_SECONDS

    def reset(self) -> float | None:
        """A new station starts at the normal cushion."""
        changed = self._step >= 0
        self._step = -1
        self._stalled = False
        self._clean_since = None
        return NORMAL_SECONDS if changed else None


def mpv_value(seconds: float) -> str:
    """The ``cache-pause-wait`` string mpv is given (pure)."""
    return f"{seconds:.1f}"


__all__ = ["CLEAN_SECONDS", "NORMAL_SECONDS", "STEPS", "CushionPolicy", "mpv_value"]

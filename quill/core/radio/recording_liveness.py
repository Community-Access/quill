"""Growth-based liveness for an in-progress radio recording.

The recorder already has two liveness signals: ffmpeg's own ``-rw_timeout``
(a network read that stalls for 30 seconds aborts the process) and
process-exit monitoring (the recorder reacts once ffmpeg dies). Both depend on
ffmpeg noticing. A stream can defeat them: a server that keeps the socket open
and dribbles keep-alive bytes, or a proxy that answers reads with nothing
useful, leaves ffmpeg alive and apparently healthy while the output file stops
growing. The recording looks fine in the Recordings list and captures silence.

This module adds the missing third signal, deliberately independent of ffmpeg:
watch the output file's *size*. Audio that is being recorded makes the file
grow, always -- every format QUILL records to writes continuously, with no
trailing-index container that defers its bytes to the end. So a file that has
not grown across several consecutive checks is not recording, whatever the
process table says.

The verdict is pure (:class:`GrowthTracker` / :func:`is_stalled`, both fed
plain ``(size, timestamp)`` samples) so it is testable without a clock, a
filesystem, or a process. :func:`wait_for_exit` is the thin wiring that
samples a real file while waiting on a real process, and hands a stall back to
the recorder's *existing* drop path -- it stops the stalled ffmpeg, which then
exits non-zero and reconnects or finalizes exactly as a genuine drop does.
Nothing about the existing signals is removed or weakened.

wx-free, strict-typed.
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "MIN_GROWTH_BYTES",
    "STALL_CHECK_COUNT",
    "STALL_CHECK_INTERVAL_SECONDS",
    "GrowthTracker",
    "is_stalled",
    "wait_for_exit",
]

#: Seconds between growth checks. Long enough that ordinary write buffering
#: (ffmpeg flushes its muxer every few seconds, not every frame) always shows
#: up as growth on a healthy recording, and that a brief rebuffer inside one
#: window cannot look like a stall; short enough that a genuinely dead stream
#: is caught in about a minute rather than at the end of the show.
STALL_CHECK_INTERVAL_SECONDS = 15.0

#: How many *consecutive* non-growing checks declare the recording stalled.
#: Four checks at the interval above means roughly one minute of a completely
#: static file before we act. A single flat check is never enough: a slow
#: network, a disk flush landing just after a sample, or a station's own
#: momentary rebuffer can all produce one. Only a sustained run of them --
#: something no healthy recording produces -- trips the verdict.
STALL_CHECK_COUNT = 4

#: Bytes of growth needed for a check to count as forward progress. One byte:
#: any real audio write is thousands, and demanding more would risk calling a
#: very low-bitrate stream dead.
MIN_GROWTH_BYTES = 1

#: A sample that arrives sooner than this fraction of the interval after the
#: previous one is not counted as a check -- it only refreshes the baseline.
#: Without it, a caller that polled in a tight loop could accumulate
#: STALL_CHECK_COUNT "non-growing" checks in milliseconds and kill a perfectly
#: healthy recording between two muxer flushes.
_MIN_SAMPLE_FRACTION = 0.5

#: Seconds a stalled ffmpeg is given to honour the graceful "q" quit before it
#: is terminated. Short: it is already not producing audio, and the graceful
#: path is only worth a moment for the chance of a properly closed container.
_STALL_STOP_GRACE_SECONDS = 5.0


@dataclass(slots=True)
class _Sample:
    """One observation of the output file: its size at a moment in time."""

    size: int
    at: float


class GrowthTracker:
    """Decides "stalled" from successive ``(size, timestamp)`` samples (pure).

    The first sample only establishes a baseline -- there is nothing to compare
    it against -- so every sample *after* the first is one check. Feeding
    ``STALL_CHECK_COUNT - 1`` non-growing checks leaves the recording alive;
    the next one declares it stalled. Any check that shows growth resets the
    run to zero, so an intermittent stream is never mistaken for a dead one.
    """

    __slots__ = ("_interval", "_min_growth", "_non_growing", "_previous", "_stall_checks")

    def __init__(
        self,
        *,
        stall_checks: int = STALL_CHECK_COUNT,
        interval_seconds: float = STALL_CHECK_INTERVAL_SECONDS,
        min_growth_bytes: int = MIN_GROWTH_BYTES,
    ) -> None:
        self._stall_checks = max(1, stall_checks)
        self._interval = max(0.0, interval_seconds)
        self._min_growth = max(1, min_growth_bytes)
        self._previous: _Sample | None = None
        self._non_growing = 0

    @property
    def non_growing_checks(self) -> int:
        """Consecutive checks that showed no growth (reset by any growth)."""
        return self._non_growing

    @property
    def stalled(self) -> bool:
        """Whether the run of non-growing checks has reached the threshold."""
        return self._non_growing >= self._stall_checks

    def sample(self, size: int, at: float) -> bool:
        """Feed one observation; returns whether the recording is now stalled.

        *size* is the output file's size in bytes (a file that does not exist
        yet counts as 0) and *at* is a monotonic timestamp in seconds.
        """
        previous = self._previous
        if previous is None:
            self._previous = _Sample(size, at)
            return False
        if at - previous.at < self._interval * _MIN_SAMPLE_FRACTION:
            # Too soon to be a real check: refresh the baseline only.
            self._previous = _Sample(size, at)
            return self.stalled
        if size - previous.size >= self._min_growth:
            self._non_growing = 0
        else:
            self._non_growing += 1
        self._previous = _Sample(size, at)
        return self.stalled


def is_stalled(
    samples: Sequence[tuple[int, float]],
    *,
    stall_checks: int = STALL_CHECK_COUNT,
    interval_seconds: float = STALL_CHECK_INTERVAL_SECONDS,
) -> bool:
    """Whether a whole sequence of ``(size, timestamp)`` samples ends stalled.

    A convenience over :class:`GrowthTracker` for callers (and tests) that
    already hold the full series.
    """
    tracker = GrowthTracker(stall_checks=stall_checks, interval_seconds=interval_seconds)
    verdict = False
    for size, at in samples:
        verdict = tracker.sample(size, at)
    return verdict


def file_size(path: Path) -> int:
    """*path*'s size in bytes; 0 if it does not exist or cannot be read.

    A missing file is genuinely "no bytes recorded yet", which is exactly what
    the tracker should see while ffmpeg is still opening its output.
    """
    try:
        return path.stat().st_size
    except OSError:
        return 0


def wait_for_exit(
    process: subprocess.Popen[bytes],
    output_path: Path,
    *,
    is_stopped: Callable[[], bool] = lambda: False,
    label: str = "",
    interval_seconds: float = STALL_CHECK_INTERVAL_SECONDS,
    stall_checks: int = STALL_CHECK_COUNT,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Wait for *process* to exit, watching *output_path* for growth.

    Returns ``True`` if the wait ended because the output stopped growing (the
    process was then stopped so the caller's ordinary drop handling runs), and
    ``False`` if the process exited on its own -- the pre-existing behaviour of
    a bare ``process.wait()``, which this replaces.

    ``is_stopped`` reports whether the user asked this recording to stop; while
    that is true, growth is not judged at all. A recording being wound down is
    *meant* to stop growing, and killing it for that would turn a clean stop
    into a truncated file.
    """
    tracker = GrowthTracker(stall_checks=stall_checks, interval_seconds=interval_seconds)
    while True:
        try:
            process.wait(timeout=interval_seconds)
            return False
        except subprocess.TimeoutExpired:
            pass
        if is_stopped():
            continue
        if not tracker.sample(file_size(output_path), clock()):
            continue
        logger.warning(
            "Radio recording %s has not grown for %d consecutive checks (~%.0fs); "
            "treating it as a stalled stream and stopping ffmpeg so the recording "
            "can reconnect or finalize.",
            label or output_path.name,
            stall_checks,
            stall_checks * interval_seconds,
        )
        stop_stalled(process)
        process.wait()
        return True


def stop_stalled(process: subprocess.Popen[bytes]) -> None:
    """End a stalled ffmpeg: ask politely with "q", then terminate.

    The graceful quit is tried first so the container is closed properly and
    the bytes already captured stay playable; a stalled ffmpeg may be wedged in
    a read and never see it, hence the short grace period and the terminate.
    """
    try:
        if process.stdin is not None:
            process.stdin.write(b"q")
            process.stdin.flush()
    except (OSError, ValueError):
        pass
    try:
        process.wait(timeout=_STALL_STOP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    if process.poll() is None:
        try:
            process.terminate()
        except OSError:
            pass

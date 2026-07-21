"""Spoken milestones for long downloads (Leasey-style progress speech).

A screen-reader user starting a multi-minute download otherwise hears only its
start ("Downloading FFmpeg") and its end ("FFmpeg installed") while the gauge
moves silently for minutes in between. :class:`MilestoneSpeaker` decides *when*
that wait should be broken by a spoken update -- every ``step_percent`` of
progress -- without the per-percent flood that would make the reader unusable.

Pure and testable: it only decides the phrase to speak; the caller owns the
announce sink (the app's screen-reader announcer) and the thread marshalling.
"""

from __future__ import annotations


class MilestoneSpeaker:
    """Emit a spoken progress update only when a new milestone is crossed.

    Milestones are the *interior* step boundaries (with ``step_percent=25``:
    25 / 50 / 75). 0% and 100% are deliberately left to the caller's own start
    and completion announcements, so a download speaks:
    "Downloading X" -> "... 25 percent" -> "50 percent" -> "75 percent" -> "X
    installed" -- never "0 percent" or a redundant "100 percent".
    """

    def __init__(self, *, label: str = "", step_percent: int = 25) -> None:
        self._label = label.strip()
        self._step = max(1, step_percent)
        self._last_bucket = 0

    def phrase_for(self, percent: int) -> str | None:
        """Return the update to speak at *percent*, or None to stay silent.

        Returns a phrase only the first time progress reaches each interior
        milestone; repeated or backward updates within the same bucket, an
        indeterminate (negative) percent, and the 0/100 endpoints all return
        None. A forward jump that skips a milestone (10 -> 60) speaks the
        highest bucket reached once, never a backlog of skipped ones.
        """
        if percent < 0:
            return None
        bucket = min(100, (percent // self._step) * self._step)
        if bucket <= self._last_bucket or bucket <= 0 or bucket >= 100:
            return None
        self._last_bucket = bucket
        return f"{self._label} {bucket} percent." if self._label else f"{bucket} percent."

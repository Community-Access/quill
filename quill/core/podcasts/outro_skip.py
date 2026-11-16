"""When "Stop this far before the end" should end an episode.

Only when playback *naturally crosses* into the last stretch. The first rule
fired whenever the position was inside it, however it got there, so resuming an
episode saved in its credits ended it at once, seeking in to hear the last
sentence ended it under you, and an episode shorter than the skip ended the
moment it started (``length - skip`` is negative). Earshot made the crossing
rule explicit in 1.2.5 (``PlaybackLogic.crossedOutroSkipBoundary``); this is the
same rule, so the two apps agree (earshot.md E1).

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = ["MAX_NATURAL_STEP_MS", "crossed_outro_boundary"]

#: A step longer than this between two polls is a seek, not listening. The
#: poll is once a second, and even five-times speed moves five seconds.
MAX_NATURAL_STEP_MS = 10_000

#: The episode must be longer than the skip by at least this much, or the skip
#: would swallow it whole.
_MIN_LEFT_MS = 2_000


def crossed_outro_boundary(
    previous_ms: int | None, current_ms: int, length_ms: int, skip_ms: int
) -> bool:
    """True when playback just moved naturally from before the boundary to after it.

    *previous_ms* is the position at the last poll, or ``None`` straight after a
    start, a resume or a seek -- which can never count as a crossing.
    """
    if previous_ms is None or skip_ms <= 0 or length_ms <= skip_ms + _MIN_LEFT_MS:
        return False
    if not (0 <= previous_ms < current_ms <= previous_ms + MAX_NATURAL_STEP_MS):
        return False
    boundary = length_ms - skip_ms
    return previous_ms < boundary <= current_ms < length_ms

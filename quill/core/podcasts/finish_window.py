"""How close to the end counts as finishing an episode.

An episode only became *played* when the player reached its true last
millisecond. Stop during the closing credits, move on to the next one, or
close Cast with half a minute left, and it kept a place at 99 percent -- so it
sat in Continue Listening as something "half-heard" that was, to the person
who heard it, finished. A listener asked for exactly this (2026-11): a finished
episode should leave Continue Listening.

``PodcastSettings.finished_within_seconds`` is the window, set globally and
per podcast. Two places read it, through this one function so they cannot
disagree:

* **leaving an episode** (stop, switch, shutdown) inside the window marks it
  played instead of saving a place; pausing never does, because a pause is a
  promise to come back;
* **Continue Listening** hides an episode whose saved place is already inside
  it, which is what clears the ones saved before the setting existed.

**Never for a short clip.** The window is only honoured past the halfway
point, so a 90-second trailer with a 60-second window is not "finished" the
moment it starts.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = ["within_finish_window"]


def within_finish_window(position_ms: int, length_ms: int, window_seconds: int) -> bool:
    """True when *position_ms* is close enough to the end to count as finished.

    False whenever the answer is not knowable: no length, no window, or a
    position that is not yet past the middle.
    """
    window_ms = max(0, int(window_seconds)) * 1000
    length = int(length_ms)
    position = int(position_ms)
    if window_ms <= 0 or length <= 0 or position <= 0:
        return False
    if position * 2 < length:
        return False
    return position >= length - window_ms

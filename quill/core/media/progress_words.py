"""How far through an episode or file, said the same way in every player.

Beside :mod:`quill.core.media.player_info` so QUILL Cast, Quill Radio and the
Media Player cannot drift apart (Jeff, 2026-11-27). Three rules:

* **Only a length worth trusting gets a percentage.** A live stream, or anything
  whose length is unknown, says no percentage at all -- never "0 percent" or
  "unknown percent", because a number that is not a measurement is worse than
  none (rule A-10).
* **Floored**, so it never says 100 percent before the end.
* **Last**, after the times, so the title still comes first.

Pure: the caller passes the engine's length and, where it has one, the feed's.
"""

from __future__ import annotations

__all__ = ["percent_phrase", "percent_through", "trusted_length_ms"]

#: How far the engine's length may differ from the feed's while an episode is
#: still buffering before the feed's is believed instead.
_BUFFERING_TOLERANCE = 0.05


def trusted_length_ms(engine_ms: int, feed_ms: int = 0, *, buffering: bool = False) -> int:
    """The length to measure against, or 0 when none can be trusted.

    The engine's (mpv's ``duration``) is preferred. When it is 0 or missing the
    feed's is used; and while a stream is still buffering, an engine length more
    than five percent away from the feed's is a guess from the bytes so far, so
    the feed's wins then too.
    """
    engine = max(0, int(engine_ms or 0))
    feed = max(0, int(feed_ms or 0))
    if engine <= 0:
        return feed
    if buffering and feed > 0 and abs(engine - feed) > feed * _BUFFERING_TOLERANCE:
        return feed
    return engine


def percent_through(position_ms: int, length_ms: int) -> int | None:
    """Whole percent through, floored; ``None`` when the length is unknown."""
    if length_ms <= 0:
        return None
    position = max(0, min(int(position_ms), int(length_ms)))
    return min(100, position * 100 // int(length_ms))


def percent_phrase(position_ms: int, length_ms: int) -> str:
    """ "32 percent", or "" when there is no trustworthy length."""
    percent = percent_through(position_ms, length_ms)
    return "" if percent is None else f"{percent} percent"

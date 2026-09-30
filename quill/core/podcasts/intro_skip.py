"""Skip the intro on a first play, and never again (ear.md R20).

The per-podcast intro skip jumps forward a few seconds when an episode starts, to
get past a sponsor read. It fired on *every* start, which makes it wrong in the
one case a listener notices: going back to hear the beginning again. You press
Previous, or you open an episode you have already heard, and the app helpfully
skips the part you deliberately came back for.

So it fires when all three of these are true:

* the episode is starting from the very beginning (not resuming),
* it has not been skipped before, and
* there is a skip configured at all.

**"Skipped before" is recorded per episode**, on the episode, so it survives a
restart -- an intro you skipped last night must not be skipped again this
morning. It is a separate fact from ``played``: an episode can be unplayed and
already intro-skipped, which is exactly the "I started it, went back, started
again" case.

A replay from the start is therefore skipped **once**, the first time, and never
after. That is the rule Earshot has, and it is also the only rule that makes the
feature safe to leave on.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from typing import Any

__all__ = ["START_TOLERANCE_MS", "mark_skipped", "skip_ms_for"]

#: How close to zero still counts as "from the beginning". A resume position of a
#: second or two is what a stop during the opening bars leaves behind, and
#: treating that as a resume would mean the intro skip never fired for anybody who
#: stopped early once.
START_TOLERANCE_MS = 3000


def skip_ms_for(settings: Any, episode: Any, start_ms: int) -> int:
    """How far to jump for this start, in milliseconds. ``0`` means do not.

    *start_ms* is where playback is about to begin, so a resume answers ``0``
    without needing to know why it is resuming.
    """
    configured = int(getattr(settings, "auto_skip_intro_seconds", 0) or 0)
    if configured <= 0:
        return 0
    if int(start_ms or 0) > START_TOLERANCE_MS:
        return 0
    if bool(getattr(episode, "intro_skipped", False)):
        return 0
    return configured * 1000


def mark_skipped(episode: Any) -> None:
    """Record that this episode's intro has been skipped once.

    Called by whoever actually performed the skip, so an episode that was never
    skipped -- because the setting was off, or it was a resume -- keeps its flag
    clear and gets the skip the first time it really starts from zero.
    """
    episode.intro_skipped = True

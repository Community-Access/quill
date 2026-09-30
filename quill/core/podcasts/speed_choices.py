"""The speeds a chooser offers, with Custom for one the keys can set (R21).

The Manager's speed dropdown offers nine values and snaps anything else to the
nearest one. That was honest while the only way to set a speed was the dropdown.
It is not any more: Speed Up and Speed Down step 0.05, so a show set to 1.15x by
the keyboard displayed as 1.25x and -- worse -- was *saved* as 1.25x the moment
anything else on the page was changed. The control quietly overwrote a value the
listener had set with a key.

So a speed that is not one of the nine gets its own entry, labelled for what it
is, and selecting anything else is the only way to leave it. The list is built
per show rather than held as a constant, because whether Custom exists depends on
the show.

Labels are derived from numbers and never parsed back. Doing it the other way
round is how a show saved at 2.0 came to display as 1.0x: ``f"{2.0:g}x"`` is
``"2x"``, which was not in a list spelled ``"2.0x"``, so the lookup missed and
fell back to normal while the episode carried on at 2x.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from quill.core.podcasts.speed_scale import clamp_speed

__all__ = ["OFFERED", "choices_for", "index_for", "speed_at"]

#: The speeds offered outright. The model permits 0.5x-5.0x and both engines hold
#: pitch across it; this is the shortlist, not the range.
OFFERED: tuple[float, ...] = (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)


def _label(value: float) -> str:
    return f"{value:g}x"


def choices_for(speed: float) -> tuple[str, ...]:
    """The labels to show, with a Custom entry when *speed* is not offered.

    Custom goes **last**, so the nine familiar values keep the positions somebody
    has learned and a new entry never shifts them.
    """
    resolved = clamp_speed(speed)
    labels = tuple(_label(value) for value in OFFERED)
    if any(abs(value - resolved) < 1e-9 for value in OFFERED):
        return labels
    return labels + (f"{_label(resolved)} (custom)",)


def index_for(speed: float) -> int:
    """Which row of :func:`choices_for` is selected for *speed*.

    An exact match is exact; anything else is the Custom row, which is the last
    one. Never the nearest offered value -- that is the snap this module exists
    to stop.
    """
    resolved = clamp_speed(speed)
    for index, value in enumerate(OFFERED):
        if abs(value - resolved) < 1e-9:
            return index
    return len(OFFERED)


def speed_at(index: int, speed: float) -> float:
    """The speed a row means. The Custom row means the speed it was built from,
    so selecting it changes nothing -- it is a statement, not a command."""
    if 0 <= index < len(OFFERED):
        return OFFERED[index]
    return clamp_speed(speed)

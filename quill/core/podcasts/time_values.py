"""Times that arrive from a publisher, made safe before anything plays them.

A chapters file, a transcript and a feed's soundbite tags all give times as
numbers somebody else wrote, and Python accepts more of them than a player
can use: ``json`` reads ``NaN`` and ``Infinity`` by default, ``float("inf")``
reads from feed XML, and ``True`` is an ``int``. Before this module, one
``Infinity`` raised ``OverflowError`` and took the whole chapter list (or the
whole feed's soundbites) with it, ``NaN`` raised ``ValueError``, ``true``
became a chapter at one second, and ``1e300`` became a chapter at a time no
episode has. Earshot rejects the same values (1.2.5, earshot.md E2).

One rule for every source: a finite number, not a boolean, at least zero and
under a week. Text is accepted only where the format is text (feed attributes,
some transcript files). Anything else is *invalid*, and each caller decides
what invalid means for it: a chapter is dropped, a cue keeps its text.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import math

__all__ = ["MAX_SECONDS", "ms_or_none", "seconds_to_ms_or_none"]

#: Longer than any episode or audiobook part anyone publishes, and small enough
#: that every later conversion (to a clock time, to an engine position) is safe.
MAX_SECONDS = 7 * 24 * 3600


def _number(value: object, *, allow_text: bool) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
    elif allow_text and isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return number if math.isfinite(number) else None


def seconds_to_ms_or_none(value: object, *, allow_text: bool = False) -> int | None:
    """A time in seconds as milliseconds, or ``None`` when it is not a usable time."""
    seconds = _number(value, allow_text=allow_text)
    if seconds is None or not 0 <= seconds < MAX_SECONDS:
        return None
    return int(round(seconds * 1000))


def ms_or_none(value: object, *, allow_text: bool = False) -> int | None:
    """A time already in milliseconds, checked the same way, or ``None``."""
    ms = _number(value, allow_text=allow_text)
    if ms is None or not 0 <= ms < MAX_SECONDS * 1000:
        return None
    return int(round(ms))

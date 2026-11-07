"""PressStreak -- counts quick repeats of one command and answers on every press.

The companion to :class:`quill.core.multi_press.MultiPressDispatcher`, kept in a
module of its own (GATE-11) and wx-free like it.
"""

from __future__ import annotations

__all__ = ["PressStreak"]


class PressStreak:
    """Counts quick repeats of one command, and answers on *every* press.

    :class:`~quill.core.multi_press.MultiPressDispatcher` waits out the
    window before it acts, which is right when the first press and the second
    do different, incompatible things (open the palette, or re-run the last
    command). A spoken readout is the opposite case: the first press should be
    heard at once, and a second press inside the window simply supersedes it --
    "say the clipboard", then "no, spell it". Waiting would put a pause in front
    of the answer people press for most.

    ``press`` returns 1, 2, ... up to the ceiling, then starts again at 1, so a
    fourth quick press of a three-level command is the first level again rather
    than nothing. A press of a *different* binding, or one after the window has
    passed, is a first press. *now* is passed in (seconds, monotonic) so the
    timing is testable without a clock.
    """

    def __init__(self, window_seconds: float = 0.5, max_count: int = 3) -> None:
        self._window = float(window_seconds)
        self._max_count = max(1, int(max_count))
        self._binding = ""
        self._count = 0
        self._at = 0.0

    def press(self, binding: str, now: float, *, max_count: int | None = None) -> int:
        """Record a press of *binding* at *now*; return which press this is."""
        ceiling = self._max_count if max_count is None else max(1, int(max_count))
        quick = binding == self._binding and 0 <= now - self._at <= self._window
        self._count = self._count + 1 if quick and self._count < ceiling else 1
        self._binding = binding
        self._at = now
        return self._count

    def reset(self) -> None:
        self._binding = ""
        self._count = 0

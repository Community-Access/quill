"""A named generation counter for deferred and background work.

The pattern appears hand-rolled at roughly ten sites (browse prewarm, studio
loads, radio play tokens, GitHub dialogs, Quillin host calls): schedule work,
bump a counter, and have the completion check the counter so a superseded
result can never deliver. Naming it makes the idiom reviewable and gives every
site the same two-line shape::

    self._gen = GenerationCounter()
    token = self._gen.advance()          # scheduling: invalidates prior work
    ...
    if not self._gen.is_current(token):  # completing: am I stale?
        return

Why it matters here specifically: a screen-reader user who arrows down four
lines quickly must hear one announcement, not four stale ones, and a
background scan that finishes after the user moved on must not replace what
they are reading. wx-free, strict-typed; not thread-safe by design — advance
on the UI thread, check from anywhere (a torn read just means the stale side
loses, which is the point).
"""

from __future__ import annotations

__all__ = ["GenerationCounter"]


class GenerationCounter:
    """Monotonic token source: only the most recently issued token is current."""

    __slots__ = ("_current",)

    def __init__(self) -> None:
        self._current = 0

    def advance(self) -> int:
        """Invalidate all outstanding work and return the new current token."""
        self._current += 1
        return self._current

    def is_current(self, token: int) -> bool:
        """True while *token* is the newest issued token."""
        return token == self._current

    @property
    def current(self) -> int:
        return self._current

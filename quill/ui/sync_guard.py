"""A guard for controls the app keeps in step with a list selection (UX-014).

A mute check box, a level spin box or a sound-card choice that shows the
selected row's state is *written by the app* every time the selection moves.
On some wx builds and controls that write raises the same event a user's
change does, and a handler that cannot tell the two apart writes the shown
value back -- TG Drop Deck's mixer muted every source the user arrowed past
that way, silently (its ``CLAUDE.md`` lines 249-262). So the app writes under
this guard, and every user-change handler returns at once while it is held::

    with self._showing:
        self.mute.SetValue(row.muted)

    def _mute_changed(self, event):
        if self._showing:
            return
        ...

Re-entrant, so a fill that selects a row (and so shows it) can nest.
"""

from __future__ import annotations

from types import TracebackType


class SyncGuard:
    """Held while the app, not the user, is changing a control."""

    def __init__(self) -> None:
        self._depth = 0

    def __bool__(self) -> bool:
        return self._depth > 0

    def __enter__(self) -> SyncGuard:
        self._depth += 1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._depth -= 1

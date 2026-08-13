"""Taking back an expansion that fired when you did not want it.

Inside QUILL's editor, pressing Backspace immediately after an expansion undoes
it, because the editor owns the text and can simply put it back. System-wide
there is no document to read -- so the same promise is kept by remembering what
was just typed and, if the very next keystroke is Backspace, typing the reverse.

The window for this is deliberately tiny. It closes on any other key, on a
change of focus, and after a few seconds, because an undo that fires later would
be worse than no undo at all: it would delete text the user has since typed.

Pure and wx-free -- the caller supplies the clock and performs the keystrokes.
"""

from __future__ import annotations

from dataclasses import dataclass

#: How long an expansion stays undoable. Long enough to notice and react,
#: short enough that it can never surprise anyone later.
UNDO_WINDOW_SECONDS = 5.0


@dataclass(slots=True)
class UndoPlan:
    """What to send to put the abbreviation back."""

    #: Characters to erase: the expansion, plus its trailing space if it added
    #: one. The trigger character is not included -- it was the user's own
    #: keystroke and stays exactly where they typed it.
    backspaces: int
    #: The text to type in its place -- the abbreviation as they typed it.
    text: str


@dataclass(slots=True)
class PendingExpansion:
    """The one expansion that could still be taken back."""

    abbreviation: str
    expanded_text: str
    trailing_space: bool
    window_handle: int
    at_seconds: float

    def plan(self) -> UndoPlan:
        return UndoPlan(
            backspaces=len(self.expanded_text) + (1 if self.trailing_space else 0),
            text=self.abbreviation,
        )


class UndoTracker:
    """Remembers the last expansion for as long as it is safely undoable."""

    __slots__ = ("_pending", "_window_seconds")

    def __init__(self, window_seconds: float = UNDO_WINDOW_SECONDS) -> None:
        self._pending: PendingExpansion | None = None
        self._window_seconds = window_seconds

    def record(
        self,
        *,
        abbreviation: str,
        expanded_text: str,
        trailing_space: bool,
        window_handle: int,
        now: float,
    ) -> None:
        self._pending = PendingExpansion(
            abbreviation=abbreviation,
            expanded_text=expanded_text,
            trailing_space=trailing_space,
            window_handle=window_handle,
            at_seconds=now,
        )

    def clear(self) -> None:
        self._pending = None

    @property
    def armed(self) -> bool:
        return self._pending is not None

    def take_undo(self, *, window_handle: int, now: float) -> UndoPlan | None:
        """The plan for a Backspace pressed right now, or None.

        Consumes the pending expansion either way: an undo happens once, and a
        Backspace that arrives too late or in another window means the moment
        has passed, so nothing should stay armed behind it.
        """
        pending = self._pending
        self._pending = None
        if pending is None:
            return None
        if now - pending.at_seconds > self._window_seconds:
            return None
        if window_handle and pending.window_handle and window_handle != pending.window_handle:
            # Focus moved. Whatever is under the caret now is not our expansion.
            return None
        return pending.plan()

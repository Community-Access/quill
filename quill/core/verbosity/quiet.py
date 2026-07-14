"""Quiet Mode and the verbosity undo stack (verbosity §9, §11).

Quiet Mode (§9) silences speech and earcons, leaving only the braille and visual
floor — the meeting-room toggle. :class:`VerbosityUndoStack` (§11) records
recent verbosity state transitions (mode toggles, override applies, profile or
channel changes) so ``Ctrl+Shift+Z`` can step them back one at a time.

Pure and wx-free: the controller owns the boolean state and announcement
phrasing; the chord binding, status-bar badge, and menu entry live in the UI
layer.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["QuietMode", "VerbosityUndoStack"]


class QuietMode:
    """The Quiet Mode on/off controller."""

    def __init__(self, *, active: bool = False) -> None:
        self._active = active

    @property
    def is_active(self) -> bool:
        return self._active

    def enter(self) -> str:
        """Turn Quiet Mode on; return the transition announcement."""
        self._active = True
        return "Quiet Mode on"

    def exit(self) -> str:
        """Turn Quiet Mode off; return the transition announcement."""
        self._active = False
        return "Quiet Mode off"

    def toggle(self) -> str:
        """Flip Quiet Mode and return the transition announcement."""
        return self.exit() if self._active else self.enter()


@dataclass(frozen=True, slots=True)
class _Transition:
    description: str
    undo: Callable[[], None]


class VerbosityUndoStack:
    """A bounded stack of reversible verbosity state transitions (§11)."""

    def __init__(self, *, max_entries: int = 20) -> None:
        self._max = max_entries
        self._stack: list[_Transition] = []

    def push(self, description: str, undo: Callable[[], None]) -> None:
        """Record a transition and how to reverse it."""
        self._stack.append(_Transition(description, undo))
        if len(self._stack) > self._max:
            self._stack.pop(0)

    def undo(self) -> str:
        """Reverse the most recent transition; announce the result.

        Returns ``"Nothing to undo"`` when the stack is empty.
        """
        if not self._stack:
            return "Nothing to undo"
        transition = self._stack.pop()
        transition.undo()
        return f"Undid {transition.description}"

    @property
    def depth(self) -> int:
        return len(self._stack)

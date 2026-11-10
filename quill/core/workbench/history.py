"""Change History and Undo for changes made on a service.

Every save the Workbench makes is a step (GitHub PRD section 16.5): what
changed, on what, and how to put it back. This module keeps the steps in
order and answers "what would Undo do now?"; the provider supplies the
inverse change, because only it knows how to remove a label or restore a
post revision. Nothing here talks to a network.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

__all__ = ["Change", "ChangeHistory"]


@dataclass(frozen=True)
class Change:
    """One change already made.

    *summary* is the sentence said after it ("#42: added bug"); *undo* and
    *redo* make the inverse and the original change again, and return the
    sentence to say. A change with no *undo* is recorded but cannot be undone
    (a deleted branch, say), and the history says so rather than pretending.
    """

    target: str
    summary: str
    undo: Callable[[], str] | None = None
    redo: Callable[[], str] | None = None
    when: float = 0.0


@dataclass
class ChangeHistory:
    """The Workbench's steps, newest last, with an undo and a redo stack."""

    limit: int = 200
    _done: list[Change] = field(default_factory=list)
    _undone: list[Change] = field(default_factory=list)

    def record(self, change: Change) -> None:
        """A new change: it can be undone, and nothing undone can be redone any more."""
        self._done.append(change)
        del self._done[: max(0, len(self._done) - self.limit)]
        self._undone.clear()

    @property
    def entries(self) -> Sequence[Change]:
        return tuple(self._done)

    def next_undo(self) -> Change | None:
        return self._done[-1] if self._done else None

    def can_undo(self) -> bool:
        change = self.next_undo()
        return change is not None and change.undo is not None

    def undo(self) -> str:
        """Undo the newest change and say what happened."""
        change = self.next_undo()
        if change is None:
            return "Nothing to undo."
        if change.undo is None:
            return f"{change.summary} cannot be undone."
        said = change.undo()
        self._undone.append(self._done.pop())
        return said

    def redo(self) -> str:
        if not self._undone:
            return "Nothing to redo."
        change = self._undone[-1]
        if change.redo is None:
            return f"{change.summary} cannot be made again."
        said = change.redo()
        self._done.append(self._undone.pop())
        return said

    def clear(self) -> None:
        self._done.clear()
        self._undone.clear()

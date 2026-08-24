"""Undo the last destructive action, once -- shared by Quill Radio and Cast.

Both apps ask before anything destructive: Unsubscribe, Remove All Episodes,
Remove All Downloads, Mark All as Played, Delete Recording. A confirmation
prompt is the cheap answer and a poor one -- it costs a keystroke and a
sentence *every single time*, including the nine hundred times the listener
meant it, and it still cannot help the one time the wrong row was focused.

One step of undo is cheaper than a prompt on every verb, and kinder than
either: do the thing, say what happened, and say that Ctrl+Z takes it back.
So this module is a **single slot**. Remembering a new action disposes of the
one before it (there is no stack to get lost in), and taking the action
empties the slot (undo is once, not a rewind).

Three things make an undo honest rather than a promise:

* **It says what would come back, before it does it.** :meth:`UndoableAction.offer`
  is the sentence Ctrl+Z speaks when there is nothing focused to guess from:
  "Undo Unsubscribe: brings back The Daily, with 412 episodes and 3 downloads."
* **It says what it cannot bring back.** ``caveat`` carries the limit in the
  same breath -- a re-queued download is not the same as a restored file, and
  saying so is the difference between an undo and a lie.
* **Deleted files are moved, not unlinked.** :func:`hold_files` moves them to
  a holding folder that only ever contains the one undoable step; the slot's
  disposer empties it when the step is displaced. No new dependency, no
  recycle-bin round trip, and Ctrl+Z genuinely restores the bytes.

The module is pure of wx and of app state: an action carries a callable the
UI supplied, and this file never learns what a podcast is.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "HELD_DIR_NAME",
    "UndoSlot",
    "UndoableAction",
    "discard_held",
    "hold_files",
    "restore_held",
]

#: The folder under an app's data directory that holds the one undoable
#: deletion. Never more than one step's worth: the slot empties it.
HELD_DIR_NAME = "undo-hold"


@dataclass(frozen=True, slots=True)
class UndoableAction:
    """One destructive step, and how to take it back.

    *verb* is the action as the menu names it ("Unsubscribe"), *subject* the
    thing it acted on ("The Daily"), *restores* what coming back would mean
    ("412 episodes and 3 downloaded files"), and *caveat* the honest limit,
    if there is one.
    """

    verb: str
    subject: str
    restores: str
    undo: Callable[[], None]
    caveat: str = ""
    #: Called when this action is displaced or the slot is cleared without
    #: being used -- the point at which held files become genuinely deleted.
    dispose: Callable[[], None] | None = None

    def _tail(self) -> str:
        return f" {self.caveat.strip().rstrip('.')}." if self.caveat.strip() else ""

    def _object(self) -> str:
        """ "The Daily, with 412 episodes" -- what comes back, in words."""
        subject = self.subject.strip() or "it"
        return f"{subject}, with {self.restores}" if self.restores.strip() else subject

    def offer(self) -> str:
        """What Ctrl+Z would do, said before doing it."""
        return f"Undo {self.verb}: brings back {self._object()}.{self._tail()}"

    def done(self) -> str:
        """What Ctrl+Z did, said after doing it."""
        return f"Undid {self.verb}. Brought back {self._object()}.{self._tail()}"


@dataclass(slots=True)
class UndoSlot:
    """One step of undo. Remembering displaces; taking empties.

    Deliberately not a stack: a listener who has to remember how many times
    to press Ctrl+Z has been given a puzzle, not an undo.
    """

    _action: UndoableAction | None = field(default=None, repr=False)

    def remember(self, action: UndoableAction) -> None:
        """Hold *action* as the one undoable step, disposing of the last."""
        self._dispose_current()
        self._action = action

    def peek(self) -> UndoableAction | None:
        return self._action

    def take(self) -> UndoableAction | None:
        """The held action, if any, and empty the slot. Does not run it."""
        action = self._action
        self._action = None
        return action

    def clear(self) -> None:
        """Forget the held step, disposing of anything it was holding."""
        self._dispose_current()
        self._action = None

    def offer_sentence(self) -> str:
        """What Ctrl+Z would do right now, for a readout or a menu label."""
        action = self._action
        if action is None:
            return "Nothing to undo."
        return action.offer()

    def menu_label(self) -> str:
        """The Edit-menu wording: "Undo Unsubscribe" / "Undo" when empty."""
        action = self._action
        return f"Undo {action.verb}" if action is not None else "Undo"

    def _dispose_current(self) -> None:
        action = self._action
        if action is None or action.dispose is None:
            return
        try:
            action.dispose()
        except Exception:  # noqa: BLE001 - a disposer bug must not break the app
            pass


# -- holding deleted files ------------------------------------------------------


def hold_files(paths: list[Path], holding_dir: Path) -> dict[Path, Path]:
    """Move *paths* aside into *holding_dir*; map held path -> original path.

    The step that replaces ``path.unlink()`` wherever a destructive verb wants
    to be undoable. Files that do not exist are skipped; a file that cannot be
    moved is left where it is and simply not held (the caller's delete then
    still has to happen, or not, on its own terms).

    Names collide across shows and folders, so each held file gets an index
    prefix -- the holding folder is emptied wholesale, never read by name.
    """
    held: dict[Path, Path] = {}
    if not paths:
        return held
    try:
        holding_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return held
    for index, original in enumerate(paths):
        try:
            if not original.exists():
                continue
            target = holding_dir / f"{index:04d}-{original.name}"
            shutil.move(str(original), str(target))
            held[target] = original
        except (OSError, shutil.Error):
            continue
    return held


def restore_held(held: dict[Path, Path]) -> int:
    """Move held files back where they came from; return how many landed."""
    restored = 0
    for target, original in held.items():
        try:
            if not target.exists():
                continue
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(original))
            restored += 1
        except (OSError, shutil.Error):
            continue
    return restored


def discard_held(held: dict[Path, Path]) -> None:
    """Delete held files for good -- the disposer of an undoable deletion."""
    for target in held:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            continue

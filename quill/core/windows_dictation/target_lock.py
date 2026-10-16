"""The field a Dictate Anywhere session was started in, and only that field.

QUILL Transcribe's spec (section 7.7): the words go into the field that had the
focus when dictation started, and nowhere else. The shared external document
(:class:`quill.ui.windows_dictation_external.ExternalDocument`) follows the
focus -- if you move to another field it carries on typing there -- which is
what Quill Inkwell did until 2026-10-13. This wrapper is the stricter rule, and
both QUILL Transcribe and Inkwell's Dictate Anywhere now dictate through it
(D-15; :func:`quill.ui.windows_dictation_external.locked_external_document`):

* **Locked at the start.** When a session starts, the field in front is
  remembered (its window, its process and, where UI Automation can say, the
  control itself).
* **Checked before every phrase.** If the focus is anywhere else when a phrase
  is ready, :meth:`LockedTarget.unavailable_reason` says so, and a controller
  that sees ``holds_phrases`` pauses and keeps the words instead of ending the
  session (:mod:`~quill.core.windows_dictation.target_hold`). Nothing is typed.
* **Moved only on purpose.** :meth:`LockedTarget.relock` is the "resume in this
  field" action: the new field is checked exactly as a new session would be,
  and becomes the locked one only if it passes.

The identity of a field comes from a ``where`` callable the host passes in, so
this module is wx-free and platform-free, and the tests drive it with fakes.
Nothing here reads the other program's text: the identity is a window handle,
a process id and a control id, never a title or a value.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

__all__ = ["MOVED", "ExternalPort", "LockedTarget"]

#: Said when the focus is no longer in the field the session started in.
MOVED = "The focus moved away from the field you started dictating in."


class ExternalPort(Protocol):
    """The parts of the shared external document this wrapper passes through."""

    def unavailable_reason(self, *, writing: bool) -> str: ...

    def context(self) -> tuple[str, str]: ...

    def selection(self) -> tuple[int, int]: ...

    def select(self, start: int, end: int) -> None: ...

    def insert(self, text: str) -> tuple[int, int]: ...

    def text_between(self, start: int, end: int) -> str: ...

    def remove(self, start: int, end: int) -> None: ...

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]: ...

    def line_bounds(self) -> tuple[int, int]: ...

    def last_position(self) -> int: ...

    def undo(self) -> bool: ...


class LockedTarget:
    """A document port that writes only into the field the session began in."""

    #: Tells the controller this document cannot be read (voice_commands.py).
    external = True
    #: Tells the controller to pause and keep phrases rather than stop
    #: (target_hold.py) when this document cannot be written to.
    holds_phrases = True

    def __init__(
        self,
        inner: ExternalPort,
        *,
        where: Callable[[], Any],
        advice: str = "",
        write_failure: str = "",
    ) -> None:
        self._inner = inner
        self._where = where
        self._locked: Any = None
        #: What to do next, added to the sentence said when a session pauses.
        self.pause_advice = advice
        #: Said when a phrase was typed only in part (target_hold.py); empty
        #: for the controller's own sentence.
        self.write_failure = write_failure

    # -- the lock --------------------------------------------------------- #

    @property
    def locked(self) -> bool:
        """Whether a field has been chosen for this session."""
        return self._locked is not None

    def on_locked_field(self) -> bool:
        """Whether the focus is in the locked field now."""
        return self._locked is not None and self._safe_where() == self._locked

    def relock(self) -> str:
        """Make the field in front the session's field: ``""``, or why not."""
        reason = str(self._inner.unavailable_reason(writing=False))
        if reason:
            return reason
        place = self._safe_where()
        if place is None:
            return "Windows cannot say which field has the focus, so nothing is typed there."
        self._locked = place
        return ""

    def release(self) -> None:
        """The session is over: the next one locks afresh."""
        self._locked = None

    def _safe_where(self) -> Any:
        try:
            return self._where()
        except Exception:  # noqa: BLE001 - "cannot tell" is never "same field"
            return None

    # -- the port ----------------------------------------------------------- #

    def unavailable_reason(self, *, writing: bool) -> str:
        if not writing:
            # A session is starting: whatever is in front now becomes its field.
            self._locked = None
            return self.relock()
        if self._locked is None:
            return MOVED
        if self._safe_where() != self._locked:
            return MOVED
        return str(self._inner.unavailable_reason(writing=True))

    def context(self) -> tuple[str, str]:
        return self._inner.context()

    def selection(self) -> tuple[int, int]:
        return self._inner.selection()

    def select(self, start: int, end: int) -> None:
        self._inner.select(start, end)

    def insert(self, text: str) -> tuple[int, int]:
        # Checked again here, at the last moment: the controller asked a moment
        # ago, but a phrase must never land somewhere the person did not choose.
        if not self.on_locked_field():
            raise OSError(MOVED)
        return self._inner.insert(text)

    def text_between(self, start: int, end: int) -> str:
        if not self.on_locked_field():
            return ""  # "scratch that" leaves another field alone, and says so
        return self._inner.text_between(start, end)

    def remove(self, start: int, end: int) -> None:
        if not self.on_locked_field():
            raise OSError("The focus has moved, so nothing was taken back.")
        self._inner.remove(start, end)

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.remove(start, end)
        return self.insert(text)

    def line_bounds(self) -> tuple[int, int]:
        return self._inner.line_bounds()

    def last_position(self) -> int:
        return self._inner.last_position()

    def undo(self) -> bool:
        return False

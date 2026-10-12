"""Paused, not stopped: what dictation does when its field cannot be written.

QUILL Transcribe's rule (spec sections 7.2 and 7.7): if the focus leaves the
field a session started in, or that field becomes unsafe, the words stop going
anywhere -- and they are not thrown away either. The session **pauses**: the
phrase that could not be written is held, so is everything said while paused,
and nothing is typed until the person chooses one of three things:

* **Resume** -- back in the field the session started in, the held phrases are
  written there, in order, and dictation carries on;
* **Resume in this field** -- the field in front now becomes the session's
  field, after the same checks a new session gets, and the held phrases go
  there;
* **Discard** -- the held phrases are dropped; still paused.

Stopping while paused says how many held phrases were not written. Only a
document that asks for this (``holds_phrases``, :mod:`target_lock`) gets it;
an editor's own document still ends the session, as it always has, because
there the "field" cannot move.

Held phrases live in memory for this session only -- never written to disk,
never logged -- and there is a ceiling, so a person who walks away from a
paused session does not fill memory with a meeting's worth of words.

Mixed into :class:`~quill.core.windows_dictation.controller.DictationController`.
wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.vocabulary import Command

if TYPE_CHECKING:
    from quill.core.windows_dictation.parser import ParsedPhrase, RecognizedPhrase
    from quill.core.windows_dictation.ports import DictationState
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["MAX_HELD", "TargetHoldMixin", "WRITE_FAILED"]

#: The most phrases kept while paused. Beyond it, new phrases are dropped and
#: the status line says so -- a held phrase is a promise, and an unbounded one
#: is not a promise anybody can keep.
MAX_HELD = 50

#: Said when a phrase could not be written at all, or only partly.
WRITE_FAILED = "Dictation stopped: the phrase could not be written into the document."


def _phrases(count: int) -> str:
    return f"{count} phrase" + ("" if count == 1 else "s")


class TargetHoldMixin:
    """Hold phrases while the session's field cannot be written; resume on request."""

    _state: DictationState
    _document: Any
    _feedback: Any
    _preferences: Callable[[], DictationPreferences]

    # Provided by the controller; declared so the mixin type-checks on its own.
    def _set_state(self, state: DictationState) -> None:
        raise NotImplementedError

    def _say(self, message: str) -> None:
        raise NotImplementedError

    def _fail(self, message: str, preferences: DictationPreferences) -> None:
        raise NotImplementedError

    def _apply(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        raise NotImplementedError

    def _parse(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> ParsedPhrase:
        raise NotImplementedError

    def _abandon(self, message: str) -> None:
        raise NotImplementedError

    def stop(self, message: str = "Dictation off.") -> None:
        raise NotImplementedError

    def _init_target_hold(self) -> None:
        self._held: list[ParsedPhrase] = []
        self._hold_reason = ""

    # -- what the host asks ------------------------------------------------- #

    @property
    def paused_for_target(self) -> bool:
        """Whether the session is paused because its field cannot be written."""
        return bool(self._hold_reason)

    @property
    def held_count(self) -> int:
        """How many phrases are waiting to be written."""
        return len(self._held)

    @property
    def hold_reason(self) -> str:
        """Why the session is paused ("" when it is not)."""
        return self._hold_reason

    # -- the controller's hooks --------------------------------------------- #

    def _hold(self, parsed: ParsedPhrase, reason: str) -> bool:
        """A phrase could not be written: hold it and pause, if the document
        asks for that. ``False`` leaves the controller to end the session."""
        from quill.core.windows_dictation.ports import DictationState

        if not getattr(self._document, "holds_phrases", False):
            return False
        first = not self._hold_reason
        self._keep(parsed)
        self._hold_reason = reason
        self._set_state(DictationState.PAUSED)
        if first:
            advice = str(getattr(self._document, "pause_advice", "") or "")
            sentence = f"Dictation paused. {reason} Nothing is typed until you resume."
            self._fail(f"{sentence} {advice}".strip(), self._preferences())
        return True

    def _holding_more(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> bool:
        """A phrase heard while paused: kept, or a command answered. ``False``
        when the session is not paused for its field."""
        from quill.core.windows_dictation.ports import DictationState

        if not self._hold_reason or self._state is not DictationState.PAUSED:
            return False
        parsed = self._parse(phrase, preferences)
        command = parsed.command
        if command is Command.STOP:
            self.stop()
        elif command is Command.SCRATCH:
            if self._held:
                self._held.pop()
                self._say(f"Took back the last held phrase. {_phrases(len(self._held))} held.")
            else:
                self._say("Nothing is held to take back.")
        elif command is not None:
            self._say("Dictation is paused. Resume it first.")
        elif parsed.pieces:
            self._keep(parsed)
        return True

    def _keep(self, parsed: ParsedPhrase) -> None:
        if len(self._held) >= MAX_HELD:
            self._feedback.show(f"Paused. {_phrases(MAX_HELD)} held; no more are kept.")
            return
        self._held.append(parsed)
        self._feedback.show(f"Paused. {_phrases(len(self._held))} held.")

    def _write_failure(self) -> str:
        """What is said when a phrase could not be written, or only partly."""
        return str(getattr(self._document, "write_failure", "") or WRITE_FAILED)

    def _held_stopping(self, message: str) -> str:
        """Stopping: drop what is held, and say how much was never written."""
        count = len(self._held)
        self._drop_held()
        if not count:
            return message
        verb = "was" if count == 1 else "were"
        return f"{message[:-1]}. {_phrases(count)} held while paused {verb} not written."

    def _drop_held(self) -> None:
        self._held = []
        self._hold_reason = ""

    # -- the person's choices ----------------------------------------------- #

    def resume_held(self, *, here: bool = False) -> bool:
        """Write the held phrases and carry on. *here* makes the field in front
        the session's field first. ``False``, with a sentence, when it cannot."""
        from quill.core.windows_dictation.ports import DictationState

        if not self._hold_reason:
            self._say("Dictation is not paused.")
            return False
        if here:
            relock = getattr(self._document, "relock", None)
            reason = str(relock()) if callable(relock) else ""
        else:
            reason = str(self._document.unavailable_reason(writing=True))
        if reason:
            if not here:
                reason += " Go back to that field, or choose Resume in This Field."
            self._say(reason)
            return False
        held, self._held = self._held, []
        self._hold_reason = ""
        self._set_state(DictationState.LISTENING)
        preferences = self._preferences()
        for index, parsed in enumerate(held):
            self._set_state(DictationState.PROCESSING)
            try:
                self._apply(parsed, preferences)
            except Exception:  # noqa: BLE001 - a failed write ends the session, never the app
                self._abandon(self._write_failure())
                return False
            if self._hold_reason:  # the field moved again part-way through
                self._held = self._held + held[index + 1 :]
                return False
            if self._state is DictationState.PROCESSING:
                self._set_state(DictationState.LISTENING)
        where = "Resumed in this field." if here else "Resumed."
        written = f" {_phrases(len(held))} written." if held else ""
        self._say(where + written)
        return True

    def discard_held(self) -> int:
        """Drop the held phrases; the session stays paused. Returns how many."""
        count = len(self._held)
        self._held = []
        if not self._hold_reason:
            self._say("Dictation is not paused.")
            return 0
        self._say(
            f"Discarded {_phrases(count)}. Still paused: resume, or stop dictation."
            if count
            else "Nothing was held. Still paused: resume, or stop dictation."
        )
        return count

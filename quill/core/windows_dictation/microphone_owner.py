"""The microphone: one across the family, and never the screen reader's voice.

**One microphone** (D-11, 2026-10-13).

QUILL, QUILL Lite, QUILL Transcribe and Quill Inkwell each run the shared
:class:`~quill.core.windows_dictation.controller.DictationController`. Each one
hands it a *microphone gate* -- a
:class:`~quill.core.dictation_owner.MicrophoneLock` naming the app -- and the
controller takes the gate before the recogniser opens and lets go of it when the
recogniser closes. That is every path out of a session (stop, an error, the
window closing, Customize Features switching dictation off), because they all
close the recogniser through one method; and the kernel lets go when the
program exits for any reason. Two starts give one owner and one recogniser: the
second is refused with a sentence naming the program already listening.

The gate is optional, so a controller built in a test against fakes has none
and behaves exactly as before.

A refusal is said like any other failed start -- the error tone when tones are
on, and the words -- except while the controller is quietly opening the
microphone for the wake phrase: then nothing is said, because the person did
not ask for anything, and the next time the window comes forward it tries
again.

**The screen reader** (moved here from the controller, GATE-11): whether the
reader was talking over a phrase, for an engine that hears the microphone
itself, and whether it cannot be heard at all (:mod:`reader_gate`).

Mixed into the controller, which supplies ``_set_state``, ``_fail``,
``_feedback`` and ``_recognizer``. wx-free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from quill.core.windows_dictation.reader_gate import started_gate

if TYPE_CHECKING:
    from quill.core.windows_dictation.ports import DictationState
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["MicrophoneGate", "MicrophoneOwnerMixin"]


class MicrophoneGate(Protocol):
    """What the controller needs of :class:`~quill.core.dictation_owner.MicrophoneLock`."""

    def take(self) -> str:
        """``""`` when this app has the microphone now, else why it cannot."""
        ...

    def release(self) -> None: ...


class MicrophoneOwnerMixin:
    """Take the family's microphone lock before listening; let go after."""

    _microphone: MicrophoneGate | None
    _feedback: Any
    _recognizer: Any

    def _set_state(self, state: DictationState) -> None:  # provided by the controller
        raise NotImplementedError

    def _fail(self, message: str, preferences: DictationPreferences) -> None:
        raise NotImplementedError

    def _microphone_refused(
        self, preferences: DictationPreferences, *, quiet: bool, report: bool
    ) -> bool:
        """``True`` when another program holds the microphone, said unless quiet."""
        gate = self._microphone
        if gate is None:
            return False
        try:
            refusal = gate.take()
        except Exception:  # noqa: BLE001 - a lock that cannot be asked never stops dictation
            return False
        if not refusal:
            return False
        from quill.core.windows_dictation.ports import DictationState

        self._set_state(DictationState.OFF)
        if report and not quiet:
            self._fail(refusal, preferences)
        return True

    def _release_microphone(self) -> None:
        gate = self._microphone
        if gate is None:
            return
        try:
            gate.release()
        except Exception:  # noqa: BLE001 - the kernel lets go at exit either way
            pass

    def _not_opened(self) -> None:
        """The recogniser would not start: off, and the microphone let go."""
        from quill.core.windows_dictation.ports import DictationState

        self._release_microphone()
        self._set_state(DictationState.OFF)

    # -- what the microphone hears: the screen reader (reader_gate.py) ---------- #

    def _reader_was_talking(self, started: float | None) -> bool:
        """For an engine that hears the microphone itself (reader_gate.py): was
        the screen reader talking for most of this phrase? The built-in models
        never hear it -- their audio is silenced at the source -- and say so."""
        gate = started_gate()
        if gate is None or started is None or not getattr(self._recognizer, "hears_reader", True):
            return False
        return gate.mostly_reader(started)

    def _reader_silenced(self) -> bool:
        """True when the screen reader cannot reach this engine at all: the
        gate is capturing it and the built-in model never hears it then. Its
        echo cannot be heard, so the same words said again are always meant
        (echo_guard.py is for every other case)."""
        gate = started_gate()
        if gate is None or not gate.readers:
            return False
        return not getattr(self._recognizer, "hears_reader", True)

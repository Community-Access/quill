"""The states dictation is in, and the three ports it drives.

Moved out of :mod:`~quill.core.windows_dictation.controller` (GATE-11) when
the 2026-10-05 gap plan gave the controller its voice commands, live
transcripts and language switch. The controller re-exports every name, so
nothing that imported them from there changes.

The ports are what an editor supplies -- the recogniser, the document and the
feedback channels -- so the whole machine runs in a unit test against fakes.
Optional extras a port may also offer (looked up with ``getattr``, so a fake
need not have them): the document's ``anchor`` family (live.py), the
feedback's ``preview``, ``say_quietly``, ``phrase_written``, ``library``,
``set_speech_language`` and ``use_context`` (voice_commands.py).

wx-free.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

__all__ = ["DictationState", "DocumentPort", "FeedbackPort", "Moment", "RecognizerPort"]


class DictationState(StrEnum):
    OFF = "off"
    STARTING = "starting"
    STANDBY = "standby"
    LISTENING = "listening"
    RECOGNIZING = "recognizing"
    PROCESSING = "processing"
    PAUSED = "paused"  # the microphone went away; still on, writing nothing
    STOPPING = "stopping"


class Moment(StrEnum):
    """The four moments dictation has a sound for."""

    ON = "on"
    PHRASE = "phrase"
    OFF = "off"
    ERROR = "error"


class RecognizerPort(Protocol):
    """A running recogniser. :meth:`start` raises :class:`DictationStartError`."""

    def start(self, microphone: str) -> None: ...

    def stop(self) -> None: ...


class DocumentPort(Protocol):
    """The document a session writes into."""

    def unavailable_reason(self, *, writing: bool) -> str:
        """Why nothing can be written, or ``""`` when it can.

        *writing* is ``False`` when a session is starting and ``True`` when a
        phrase is about to go in. The difference is focus: the key that starts
        dictation may arrive while a menu or the Command Palette still holds
        it, but a phrase must only ever land in the document the user is in.
        """
        ...

    def context(self) -> tuple[str, str]:
        """The text just before the selection, and just after it."""
        ...

    def selection(self) -> tuple[int, int]: ...

    def select(self, start: int, end: int) -> None: ...

    def insert(self, text: str) -> tuple[int, int]:
        """Replace the selection with *text*; return the range it now occupies."""
        ...

    def text_between(self, start: int, end: int) -> str: ...

    def remove(self, start: int, end: int) -> None: ...

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        """Put *text* where ``start..end`` was; return the range it occupies."""
        ...

    def line_bounds(self) -> tuple[int, int]:
        """Where the caret's line starts and ends."""
        ...

    def last_position(self) -> int: ...

    def undo(self) -> bool:
        """Undo the last edit; ``False`` when there was nothing to undo."""
        ...


class FeedbackPort(Protocol):
    """Sounds, speech, the status line, and the commands list."""

    def has_cue(self, moment: Moment) -> bool: ...

    def cue(self, moment: Moment) -> None: ...

    def say(self, text: str) -> None: ...

    def read_back(self, text: str) -> None:
        """Speak the words a phrase wrote. Separate from :meth:`say` because the
        host has to time it against the editor's own reaction to the edit."""
        ...

    def show(self, text: str) -> None: ...

    def state_changed(self, state: DictationState) -> None: ...

    def show_commands(self) -> None:
        """Open the list of everything dictation understands."""
        ...

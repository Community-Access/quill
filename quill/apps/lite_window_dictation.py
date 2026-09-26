"""QUILL Lite's half of Windows Dictation: the four cues, and nothing else.

Every command, sentence and rule is the shared module's
(:mod:`quill.ui.windows_dictation_commands`), which QUILL runs too. What is here
is the one thing that cannot be shared: the sound audit credits an app only
with the cues its *own* files post, so QUILL Lite names the four it plays --
and the Sound Scheme window lists exactly those, so each can be changed or
switched off.
"""

from __future__ import annotations

from quill.core.sound_events import SoundEvent
from quill.ui.windows_dictation_commands import WindowsDictationMixin

__all__ = ["DocumentDictationMixin", "dictation_cell"]

_LITE_DICTATION_CUES: frozenset[str] = frozenset({
    SoundEvent.WINDOWS_DICTATION_ON,
    SoundEvent.WINDOWS_DICTATION_PHRASE,
    SoundEvent.WINDOWS_DICTATION_OFF,
    SoundEvent.WINDOWS_DICTATION_ERROR,
})


class DocumentDictationMixin(WindowsDictationMixin):
    """Windows Dictation in a QUILL Lite document window."""

    def _dictation_cue(self, event: str) -> None:
        if event in _LITE_DICTATION_CUES:
            self._cue(event)


def dictation_cell(frame: object) -> str:
    """The status bar's Dictation cell: "Off" unless dictation says otherwise.

    A module function reached defensively, because the status mixin is composed
    onto hosts that need not carry dictation, and a missing method would take
    the whole status refresh down with it.
    """
    state = getattr(frame, "dictation_state_text", None)
    text = str(state()) if callable(state) else ""
    return text.split(": ", 1)[-1].capitalize() if text else "Off"

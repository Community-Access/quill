"""QUILL Lite's half of Windows Dictation: the seven cues, the word list, and
which of its own formatting commands bold and headings by voice may run (D-23).

Every command, sentence and rule is the shared module's
(:mod:`quill.ui.windows_dictation_commands`), which QUILL runs too. What is here
is the one thing that cannot be shared: the sound audit credits an app only
with the cues its *own* files post, so QUILL Lite names the seven it plays --
and the Sound Scheme window lists exactly those, so each can be changed or
switched off. And which word list it uses (dict.md D-12): its own
``dictation.md``, or, when the person checks "Use the shared word list" in My
Words and Phrases, the one QUILL, QUILL Transcribe and Quill Inkwell read. A
portable copy keeps its own.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.sound_events import SoundEvent
from quill.core.windows_dictation.words_exchange import SharedWords
from quill.ui.windows_dictation_commands import WindowsDictationMixin

__all__ = ["DocumentDictationMixin", "dictation_cell"]

_LITE_DICTATION_CUES: frozenset[str] = frozenset({
    SoundEvent.WINDOWS_DICTATION_ON,
    SoundEvent.WINDOWS_DICTATION_PHRASE,
    SoundEvent.WINDOWS_DICTATION_OFF,
    SoundEvent.WINDOWS_DICTATION_ERROR,
    # The working tick (2026-10-13), off unless chosen in More Dictation Settings.
    SoundEvent.WINDOWS_DICTATION_WORKING,
    # The command word heard, and command mode ended (D-1, 2026-10-15).
    SoundEvent.WINDOWS_DICTATION_COMMAND_ON,
    SoundEvent.WINDOWS_DICTATION_COMMAND_OFF,
})


class DocumentDictationMixin(WindowsDictationMixin):
    """Windows Dictation in a QUILL Lite document window."""

    def _dictation_cue(self, event: str) -> None:
        if event in _LITE_DICTATION_CUES:
            self._cue(event)

    def _dictation_shared_words(self) -> SharedWords | None:
        """The own-or-shared choice, or ``None`` in a portable copy."""
        from quill.core.lite.paths import _portable_root
        from quill.core.speech.dictation_profile import default_profile_path

        if _portable_root() is not None:
            return None
        app = self.app  # type: ignore[attr-defined]

        def set_on(on: bool) -> None:
            app.settings.share_quill_dictation_words = on
            app.save_settings()

        return SharedWords(
            own_path=Path(app.data_dir) / "dictation.md",
            shared_path=default_profile_path(),
            is_on=lambda: bool(getattr(app.settings, "share_quill_dictation_words", False)),
            set_on=set_on,
        )

    def _dictation_formatting(self) -> str:
        """``rich`` in a rich document, where QUILL Lite's own Bold, Italic and
        Heading commands apply (D-23); ``""`` otherwise."""
        editor = getattr(self, "editor", None)
        return "rich" if getattr(editor, "mode", "") == "rich" else ""

    def _dictation_apply_style(self, style: str) -> str | None:
        """QUILL Lite's own command on the selection; it says the outcome itself."""
        command = getattr(self, f"cmd_{style}", None)
        if not callable(command) or not self._dictation_formatting():
            return None
        command()
        return ""

    def _dictation_profile_path(self) -> Path:
        """QUILL Lite's own ``dictation.md``, or the shared one when chosen."""
        shared = self._dictation_shared_words()
        if shared is None:
            return Path(self.app.data_dir) / "dictation.md"  # type: ignore[attr-defined]
        return shared.current_path()


def dictation_cell(frame: object) -> str:
    """The status bar's Dictation cell: "Off" unless dictation says otherwise.

    A module function reached defensively, because the status mixin is composed
    onto hosts that need not carry dictation, and a missing method would take
    the whole status refresh down with it.
    """
    state = getattr(frame, "dictation_state_text", None)
    text = str(state()) if callable(state) else ""
    shown = text.split(": ", 1)[-1] if text else "Off"
    # Only the first letter: the live preview ("hearing: Can you send it")
    # carries the speaker's own capitals, which capitalize() would flatten.
    return shown[:1].upper() + shown[1:]

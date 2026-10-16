"""Speak a Command (F11), in both editors: the keyboard way to the command word.

D-1, 2026-10-15. The spoken command word ("QUILL scratch that") marks one
utterance as a command; this is the same thing for somebody who would rather
press a key, or whose engine keeps mishearing the word. One press: the next
thing said is a command, with or without the word. A second press before it:
command mode, until "dictation mode", a third press, or a few seconds with no
command. Everything it does is the shared controller's
(:meth:`~quill.core.windows_dictation.command_mode_mixin.CommandModeMixin.command_key`);
this is only the key.

**F11, free in both editors** (rule 2), beside the dictation keys: Ctrl+F11
dictates, Shift+F11 is Recent Phrases, Ctrl+Shift+F11 switches the language.
Neither editor uses F11 for anything; Word's F11 moves to the next field, which
neither editor has (so rule 1 claims nothing), Notepad gives it no meaning, and
it is not a screen reader's key. QUILL Transcribe answers the same
chord in its own window and offers a system-wide Command Key of the person's
choosing (``quill/apps/transcribe_keys.py``).

Pressed while dictation is off, it starts dictation here and arms one command,
because that is what pressing it asks for.
"""

from __future__ import annotations

from typing import Any

__all__ = ["DictationCommandKeyMixin"]


class DictationCommandKeyMixin:
    """The Speak a Command command, mixed into both editors' dictation."""

    def cmd_dictation_command(self) -> None:
        """Speak a Command: the next phrase is a command; twice, command mode."""
        from quill.ui.windows_dictation_commands import dictation_active

        host: Any = self
        preferences = host._dictation_preferences()
        if preferences.engine == "voice_typing":
            host._dictation_say(
                "Commands work with QUILL's own dictation. Windows voice typing has its own."
            )
            return
        controller = host._dictation_controller()
        if controller.transcribing:
            host._dictation_say("A live transcript writes every word; it takes no commands.")
            return
        if not dictation_active(self):
            host._dictation_target(self)  # here, as Ctrl+F11 would be
            if not controller.active:
                controller.start()
            if not controller.active:
                return  # it said why
        controller.command_key()

    def _dictation_my_words(self) -> list[str]:
        """This editor's My Words vocabulary: the command word may not be one."""
        from quill.core.windows_dictation.profile import load

        host: Any = self
        try:
            return list(load(host._dictation_profile_path()).vocabulary)
        except Exception:  # noqa: BLE001 - no words is a fine answer
            return []

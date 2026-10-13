"""QUILL Transcribe's dictation keys, against the editors' (D-14, 2026-10-13).

QUILL Transcribe runs the same dictation as QUILL and QUILL Lite, so where it
has the same command it answers the same key (family rule 2): somebody who
learned Ctrl+F11 in an editor should not have to learn Ctrl+D here. The keys
are read from :data:`quill.core.keymap.DEFAULT_KEYMAP`, never retyped, so the
menu cannot drift from the editors.

Three tables, and ``tests/unit/ui/test_dictation_parity.py`` holds every
editor dictation command to exactly one of the first and the last:

* :data:`SHARED_COMMANDS` -- the editor's command, and the QUILL Transcribe
  method its chord runs here. The menu shows the editors' chord.
* :data:`ALIASES` -- the key each of those had in QUILL Transcribe 1.0, kept as
  a second key rather than moved (rule 5): it is in the 1.0 user guide, and
  nothing else here wants it. The menu shows one key; both work.
* :data:`DIVERGENCES` -- the editors' dictation commands QUILL Transcribe does
  not have, each with the reason, in words (rule 11). The chord stays free.

wx-free.
"""

from __future__ import annotations

__all__ = ["ALIASES", "DIVERGENCES", "PREFERENCES_OFF", "SHARED_COMMANDS", "chord"]

#: The shared dictation settings QUILL Transcribe always runs with switched
#: off, and why. Every other setting is the editors', under the editors' name
#: and cleaned by the same loader.
PREFERENCES_OFF: dict[str, str] = {
    "wake_enabled": (
        "The wake phrase listens while an editor is the window in front, and "
        "starts dictation in that window. QUILL Transcribe types into whichever "
        "program is in front, and a program that starts typing because it heard "
        "a phrase could type into anything."
    ),
    "hold_to_talk": (
        "Holding the key to talk follows the editors' Ctrl+F11 as it is held. "
        "QUILL Transcribe's start and stop key is registered with Windows, which "
        "reports the press and never the release."
    ),
}

#: The editor's command id -> the QUILL Transcribe method its chord runs.
SHARED_COMMANDS: dict[str, str] = {
    # Ctrl+F11: start or stop. From the window it waits for the field you
    # switch to (the window itself is never dictated into).
    "tools.windows_dictation_toggle": "start_or_stop_from_here",
    # Alt+Shift+F6: the same Dictation Settings window as both editors.
    "tools.windows_dictation_settings": "edit_dictation_settings",
    # Alt+Shift+F10: the same My Words and Phrases window, over the same list.
    "tools.windows_dictation_words": "edit_dictation_words",
    # Shift+F11: the last twenty phrases of this run, newest first; Insert
    # Again types one into the program you go back to (transcribe_recent.py).
    "tools.windows_dictation_recent": "show_recent_phrases",
    # Ctrl+Shift+F11: English to Spanish and back, kept for next time.
    "tools.windows_dictation_switch_language": "switch_dictation_language",
    # Shift+F5: a recording into text, with dictation's models.
    "tools.windows_dictation_transcribe_file": "transcribe_a_recording",
}

#: QUILL Transcribe method -> the key it had in 1.0, still answered (rule 5).
ALIASES: dict[str, str] = {
    "start_or_stop_from_here": "Ctrl+D",
    "edit_dictation_settings": "Ctrl+,",
    "transcribe_a_recording": "Ctrl+O",
}

#: The editors' dictation commands that QUILL Transcribe does not have, and why.
DIVERGENCES: dict[str, str] = {
    "tools.windows_dictation_live_transcript": (
        "A live transcript writes into a new QUILL document for as long as "
        "somebody else talks. QUILL Transcribe has no documents to write one into; "
        "QUILL and QUILL Lite do."
    ),
    "tools.windows_dictation_context": (
        "Dictation Context belongs to a document, and QUILL Transcribe types into "
        "other programs' fields, whose text it never reads."
    ),
    "tools.dictation_status": (
        "QUILL Transcribe's window is its status: the State field, which has the "
        "focus when the window opens, and the tray icon's name say what dictation "
        "is doing. A key to say it again would repeat the window."
    ),
    "tools.dictation_tidy": (
        "Tidy Dictated Text rewrites text already in the document. QUILL "
        "Transcribe cannot read the other program's text (anywhere.EXTERNAL_COMMANDS), "
        "so there is nothing for it to tidy."
    ),
}


def chord(command_id: str) -> str:
    """The editors' default chord for *command_id*."""
    from quill.core.keymap import DEFAULT_KEYMAP

    return str(DEFAULT_KEYMAP[command_id])

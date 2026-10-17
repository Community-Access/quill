"""QUILL Transcribe's tutorials, and the commands its lessons can name (D-25).

:data:`CATALOGUE` is what the shared Tutorials window
(:mod:`quill.ui.tutorials_window`) and the generated book
(``standalone/transcribe/docs/tutorials.md``, GATE-TUTDOC) both read.

:data:`LOCAL_COMMANDS` is QUILL Transcribe's own small command table: the id a
lesson step names, the frame method it runs, and its key. The menu reads its
keys from here, the Tutorials window's Try It runs the method, and the book
renders the key -- one table, so the three cannot disagree. The editors'
dictation commands QUILL Transcribe shares keep the editors' ids and chords
(:mod:`quill.core.transcribe.parity`).

wx-free.
"""

from __future__ import annotations

from quill.core.transcribe.parity import SHARED_COMMANDS, chord
from quill.core.tutorials.model import Track, TutorialSet
from quill.core.tutorials.transcribe_lessons import transcribe_lessons

__all__ = ["CATALOGUE", "LOCAL_COMMANDS", "TITLE", "key_for", "method_for"]

TITLE = "QUILL Transcribe Tutorials"

#: Lesson command id -> (the frame method, its key).
LOCAL_COMMANDS: dict[str, tuple[str, str]] = {
    "transcribe.practice": ("open_practice", "Ctrl+Shift+P"),
    "transcribe.practice_start": ("practice_start_or_stop", "Ctrl+F11"),
    "transcribe.tutorials": ("open_transcribe_tutorials", "Ctrl+Alt+F1"),
    "transcribe.profile": ("choose_dictation_profile", "Ctrl+Shift+F"),
    "transcribe.profile_lock": ("toggle_profile_lock", "Ctrl+Shift+L"),
    "transcribe.resume": ("resume_dictation", "Ctrl+R"),
}

_TRACKS = (
    Track(
        "dictation",
        "Dictating with QUILL Transcribe",
        "From a first sentence in the Practice window to dictating, correcting and "
        "reviewing in any program.",
    ),
)

CATALOGUE = TutorialSet("transcribe", _TRACKS, transcribe_lessons("dictation"))


def key_for(command_id: str) -> str:
    """The key *command_id* has in QUILL Transcribe, or ``""``."""
    if command_id in LOCAL_COMMANDS:
        return LOCAL_COMMANDS[command_id][1]
    if command_id in SHARED_COMMANDS:
        return chord(command_id)
    return ""


def method_for(command_id: str) -> str:
    """The QUILL Transcribe method *command_id* runs, or ``""``."""
    if command_id in LOCAL_COMMANDS:
        return LOCAL_COMMANDS[command_id][0]
    return SHARED_COMMANDS.get(command_id, "")

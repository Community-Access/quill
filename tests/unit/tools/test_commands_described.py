"""GATE-DESCRIBE: every default chord command has an authored spoken title.

EdSharp's ``checkCommandsDescribed``, imported 2026-08-27. The QUILL Key
cheat sheet (``quill.core.quill_key_help``) is the editor's Key Describer
surface: it derives a title from the command id when no authored one exists,
which keeps *user-defined* chords speakable but let forty shipped defaults
fall back to machine-derived names. Both directions are pinned:

* every ``Ctrl+Shift+Grave`` chord in ``DEFAULT_KEYMAP`` carries an authored
  title in ``_CHORD_COMMAND_TITLES``;
* every authored title names a command that still exists, so the table
  cannot silently rot as commands are renamed.

The key each entry *shows* cannot lie by construction -- the cheat sheet
reads the live binding lookup, not a second table.
"""

from __future__ import annotations

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.quill_key_help import _CHORD_COMMAND_TITLES


def _default_chord_commands() -> list[str]:
    return [
        command_id
        for command_id, binding in DEFAULT_KEYMAP.items()
        if binding.startswith("Ctrl+Shift+Grave")
    ]


def test_every_default_chord_command_has_an_authored_title() -> None:
    missing = [c for c in _default_chord_commands() if c not in _CHORD_COMMAND_TITLES]
    assert missing == [], (
        "Chord commands whose Key Describer title is machine-derived; author "
        "one in _CHORD_COMMAND_TITLES: " + ", ".join(missing)
    )


def test_no_authored_title_names_a_dead_command() -> None:
    stale = [c for c in _CHORD_COMMAND_TITLES if c not in DEFAULT_KEYMAP]
    assert stale == [], (
        "_CHORD_COMMAND_TITLES entries for commands no longer in "
        "DEFAULT_KEYMAP: " + ", ".join(stale)
    )


def test_titles_are_speakable() -> None:
    """No empty titles, no raw id fragments leaking into speech."""
    for command_id, title in _CHORD_COMMAND_TITLES.items():
        assert title.strip(), command_id
        assert "_" not in title and "." not in title.rstrip("."), (command_id, title)

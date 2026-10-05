"""Dictate Anywhere: dictation's own engines, typing into other programs.

dict.md 3.9 (gap 8), with the owner's answer to question 9: Quill Inkwell hosts
it, because Inkwell already runs in the tray, already has system-wide keys and
already types text into other programs. Both editors can start it (More
Dictation Settings, **Dictate in Other Programs...**), and it runs the same
shared controller, engines, words and commands -- so neither editor is behind,
and the capability lives in shared code.

This module is the wx-free part:

* **What works in another program.** Punctuation and layout, spelling, the
  capital and spacing modes, the language switch, "scratch that" (sent as
  backspaces, only while the same window still has the focus), "stop
  dictation". Nothing that needs to read the other program's text -- select,
  go to, correct, units, the clips and snippets -- because Inkwell cannot see
  it: :data:`EXTERNAL_COMMANDS`.
* **The settings handed over.** Starting it from an editor writes that
  editor's dictation settings to a small file in the shared data folder
  (:func:`write_handoff`); Inkwell takes them when it starts or comes forward
  (:func:`take_handoff`) and keeps its own copy, so it can run without the
  editor afterwards. Kept in Inkwell's own settings file, so a portable copy
  keeps it in the portable folder.
* **The read-back defaults to a tone** in Inkwell: the screen reader echoes the
  typed characters itself when its typing echo is on, and words said twice are
  worse than once.

wx-free.
"""

from __future__ import annotations

from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from quill.core.windows_dictation.settings_fields import DictationSettings, load_fields
from quill.core.windows_dictation.vocabulary import Command

__all__ = [
    "EXTERNAL_COMMANDS",
    "HANDOFF_FILE",
    "dictation_fields",
    "external_refusal",
    "settings_from",
    "stored_from",
    "take_handoff",
    "write_handoff",
]

HANDOFF_FILE = "dictate-anywhere.json"

#: The commands that still make sense when the words go into another program.
#: Everything else is answered with :func:`external_refusal`.
EXTERNAL_COMMANDS = frozenset({
    Command.SCRATCH,
    Command.STOP,
    Command.HELP,
    Command.READ_BACK,
    Command.SPELL_ON,
    Command.SPELL_OFF,
    Command.SPELL_WORDS,
    Command.CAPS_ON,
    Command.CAPS_OFF,
    Command.ALL_CAPS_ON,
    Command.ALL_CAPS_OFF,
    Command.NO_SPACE_ON,
    Command.NO_SPACE_OFF,
    Command.SWITCH_SPANISH,
    Command.SWITCH_ENGLISH,
})

#: A read-back of a tone, for a mode where the screen reader echoes the typing.
_ANYWHERE_DEFAULTS: dict[str, Any] = {"windows_dictation_phrase_feedback": "sound"}


def external_refusal() -> str:
    """What is said when a command needs to read the other program's text."""
    return (
        "That works in QUILL's own documents. In another program, say the words "
        "again, or scratch that."
    )


def dictation_fields(settings: object) -> dict[str, Any]:
    """Every dictation setting *settings* has, under the shared names."""
    names = [field.name for field in fields(DictationSettings)]
    return {name: getattr(settings, name) for name in names if hasattr(settings, name)}


def settings_from(stored: dict[str, Any] | None) -> DictationSettings:
    """A settings object for the shared windows, from Inkwell's stored copy."""
    data = {**_ANYWHERE_DEFAULTS, **(stored or {})}
    cleaned = load_fields(data)
    known = {field.name for field in fields(DictationSettings)}
    return DictationSettings(**{name: value for name, value in cleaned.items() if name in known})


def stored_from(settings: DictationSettings) -> dict[str, Any]:
    """What Inkwell writes back after its Dictation Settings window."""
    return dict(asdict(settings))


def write_handoff(data_dir: Path, settings: object) -> Path:
    """Hand an editor's dictation settings to Inkwell; returns the file."""
    from quill.core.storage import write_json_atomic

    path = Path(data_dir) / HANDOFF_FILE
    write_json_atomic(path, {"schema": 1, "dictation": dictation_fields(settings)})
    return path


def take_handoff(data_dir: Path) -> dict[str, Any] | None:
    """The settings an editor handed over, once: the file is removed."""
    import json

    path = Path(data_dir) / HANDOFF_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        path.unlink()
    except OSError:
        pass
    stored = data.get("dictation") if isinstance(data, dict) else None
    return dict(stored) if isinstance(stored, dict) else None

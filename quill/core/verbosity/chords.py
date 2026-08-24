"""Which chord fires which verb -- the map the per-chord editor edits against.

The verbosity engine has always resolved a **per-chord override** ahead of a
per-verb one (``engine._resolve_template``): "when *this key* causes this verb,
say *this* instead". It is the right precedence, because the same verb read
aloud in two situations wants two different sentences -- ``nav.next_word``
after Ctrl+Right is a word you asked for, and the identical verb after a Find
is a word you were taken to.

What was missing was the list. ``CustomProfile.per_chord_overrides`` is keyed
by a chord label, and nothing in the tree ever produced the set of labels worth
offering, so the editor that edits them had no way to be opened (list.md 12.3).

Two sources, because chords come from two places:

* **Fixed editing keys.** Ctrl+Right means "next word" in every text field on
  the platform. These are not in QUILL's keymap because they were never
  QUILL's to bind, and they are precisely the chords whose announcements a
  screen-reader user hears hundreds of times an hour.
* **Bound commands.** Ctrl+S is Save *today*; a user who rebinds it should see
  their key in this list tomorrow. Those are read live from the keymap, so the
  label follows the binding rather than a copy of it made once.

The second source needs a correspondence table because a command id and a verb
id are different vocabularies on purpose: ``file.save`` is a thing you do and
``doc.save`` is a thing that gets announced. Only pairs where the command
genuinely causes the verb belong in :data:`COMMAND_VERBS` -- an invented pair
would offer an override that never fires, which is worse than an absent one.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["EDITING_CHORDS", "COMMAND_VERBS", "chord_verbs"]

#: Platform editing keys and the verb each one fires. Fixed rather than looked
#: up: these are the OS text-field bindings, so QUILL neither owns nor can
#: rebind them, and a user who wants "Ctrl+Right" reworded means that key.
EDITING_CHORDS: Mapping[str, str] = {
    "Left": "nav.previous_character",
    "Right": "nav.next_character",
    "Up": "nav.previous_line",
    "Down": "nav.next_line",
    "Ctrl+Left": "nav.previous_word",
    "Ctrl+Right": "nav.next_word",
    "Ctrl+Home": "nav.document_start",
    "Ctrl+End": "nav.document_end",
    "Backspace": "edit.delete_character",
    "Ctrl+Backspace": "edit.delete_word",
}

#: Command id -> the verb that command's announcement uses. Deliberately
#: short: a pair belongs here only when running the command is what causes the
#: verb to speak.
COMMAND_VERBS: Mapping[str, str] = {
    "file.open": "doc.open",
    "file.save": "doc.save",
    "file.save_as": "doc.save_as",
    "edit.find": "search.find",
    "edit.find_next": "search.find_next",
    "edit.find_previous": "search.find_previous",
    "edit.replace": "search.replace",
    "edit.replace_all": "search.replace_all",
    "edit.unquote_lines": "edit.unquote_lines",
}


def chord_verbs(
    keymap: Mapping[str, str] | None = None,
    *,
    known_verbs: frozenset[str] | set[str] | None = None,
) -> dict[str, str]:
    """Return ``{chord label: verb id}`` for every chord worth overriding.

    ``keymap`` is the live command bindings (``keymap.load_keymap()``); pass
    ``None`` to offer the fixed editing keys alone, which is the right answer
    for a surface with no document keymap loaded.

    ``known_verbs`` filters the result to verbs a registry actually knows. A
    chord offered for a verb that no longer exists would accept a template and
    then never speak it, so an unknown verb is dropped rather than shown.
    """
    found = dict(EDITING_CHORDS)
    for command, verb in COMMAND_VERBS.items():
        chord = (keymap or {}).get(command, "").strip()
        if chord:
            # A rebind wins over the fixed table: the user's key is the one
            # they will press, and two entries for one verb is not a menu.
            found[chord] = verb
    if known_verbs is not None:
        found = {chord: verb for chord, verb in found.items() if verb in known_verbs}
    return found

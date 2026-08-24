"""The chord list the per-chord editor edits against (list.md 12.3).

``VerbosityChordEditorDialog`` was written, tested and unreachable for two
releases, and the reason it stayed unreachable is visible in its signature: it
takes a ``chord_verbs`` map that nothing in the tree produced. The dialog was
not missing a button so much as missing its data.

These are the rules that make the data trustworthy: a chord offered here must
fire the verb it claims, and a rebound key must be the one shown.
"""

from __future__ import annotations

from quill.core.verbosity import chords
from quill.core.verbosity.registry import default_registry


def test_every_offered_verb_is_a_verb_the_registry_knows() -> None:
    """An override on a verb that does not exist is accepted and then silent.

    Both tables are hand-written against the registry, so this is the check
    that catches a verb being renamed out from under one of them.
    """
    known = {verb.id for verb in default_registry().all()}

    for chord, verb in {**chords.EDITING_CHORDS, **chords.COMMAND_VERBS}.items():
        assert verb in known, f"{chord} offers {verb}, which no registry verb answers to"


def test_every_command_in_the_table_is_a_real_bindable_command() -> None:
    """The other half: a command id that no keymap has is a row that can never
    contribute a chord, and it would sit there looking correct."""
    from quill.core.keymap import DEFAULT_KEYMAP

    for command in chords.COMMAND_VERBS:
        assert command in DEFAULT_KEYMAP, f"{command} is not a bindable command"


def test_the_fixed_editing_keys_are_offered_with_no_keymap_at_all() -> None:
    """Ctrl+Right means "next word" whether or not a document keymap loaded --
    it is the platform's binding, not QUILL's."""
    found = chords.chord_verbs(None)

    assert found["Ctrl+Right"] == "nav.next_word"
    assert found["Backspace"] == "edit.delete_character"


def test_a_bound_command_contributes_its_current_key() -> None:
    found = chords.chord_verbs({"file.save": "Ctrl+S"})

    assert found["Ctrl+S"] == "doc.save"


def test_a_rebound_command_shows_the_key_the_user_will_actually_press() -> None:
    """The reason the keymap is read live rather than copied: an override
    attached to a key the user no longer presses is an override that never
    fires, and they would have no way to tell."""
    found = chords.chord_verbs({"file.save": "F12"})

    assert found["F12"] == "doc.save"
    assert "Ctrl+S" not in found


def test_an_unbound_command_contributes_nothing_rather_than_a_blank_row() -> None:
    found = chords.chord_verbs({"file.save": "  "})

    assert "" not in found
    assert "  " not in found
    assert "doc.save" not in found.values()


def test_unknown_verbs_are_dropped_when_a_registry_is_supplied() -> None:
    """The editor validates a template against the verb; a verb it cannot
    resolve would take the template and quietly do nothing with it."""
    found = chords.chord_verbs({"file.save": "Ctrl+S"}, known_verbs={"doc.save"})

    assert found == {"Ctrl+S": "doc.save"}


def test_the_real_registry_keeps_the_whole_table() -> None:
    """Nothing is filtered out in practice -- if this starts failing, a verb
    was renamed and one of the tables above did not follow."""
    known = {verb.id for verb in default_registry().all()}

    assert chords.chord_verbs(None, known_verbs=known) == dict(chords.EDITING_CHORDS)

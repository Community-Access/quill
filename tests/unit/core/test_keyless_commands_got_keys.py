"""Rule 8: a registered editor command has a key, or a written reason not to.

A capability with no key is not merely slower to reach. It is absent from the
generated keyboard reference, so nobody discovers it either -- it exists only
for whoever happens to walk the menu it lives in. Fifteen QUILL commands were
registered with ``binding=None`` while QuillLite reached the same verb on a
chord, which is the small product being ahead of the big one in exactly the way
``CLAUDE.md`` forbids.

Every chord asserted here was **free in QUILL** when it was taken: nothing was
displaced, which is why fifteen could land in one pass. The two that needed a
displacement are asserted separately below, with what moved and why.
"""

from __future__ import annotations

import pytest

from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS


def _lite() -> dict[str, str]:
    return {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}


#: QUILL command -> (its chord, the QuillLite handler that already used it).
_ADOPTED = {
    "file.page_setup": ("Ctrl+Alt+P", "cmd_page_setup"),
    "edit.remove_duplicate_lines": ("Ctrl+Alt+D", "cmd_remove_duplicate_lines"),
    "edit.sort_lines_ascending": ("Ctrl+Alt+S", "cmd_sort_lines"),
    "format.upper_case": ("Ctrl+Shift+U", "cmd_upper_case"),
    "format.title_case": ("Ctrl+Shift+T", "cmd_title_case"),
    "navigate.next_heading": ("Ctrl+Alt+H", "cmd_next_heading"),
    "navigate.set_language": ("Ctrl+Alt+F6", "cmd_set_language"),
    "power.describe_character": ("Ctrl+Shift+C", "cmd_describe_character"),
    "edit.say_selected": ("Ctrl+Shift+Y", "cmd_say_selection"),
    "edit.copy_to_next_slot": ("Ctrl+Alt+Y", "cmd_copy_to_tray"),
    "edit.clear_all_tray_slots": ("Ctrl+Alt+Shift+Y", "cmd_clear_copy_tray"),
    "view.toggle_spellcheck_as_you_type": ("Ctrl+Alt+F7", "cmd_toggle_live_spelling"),
    "tools.check_updates": ("Ctrl+Alt+U", "cmd_check_updates"),
    "help.about_quill": ("Shift+F1", "cmd_about"),
}


@pytest.mark.parametrize(("command_id", "expected"), sorted(_ADOPTED.items()))
def test_each_adopted_command_uses_quilllites_chord(
    command_id: str, expected: tuple[str, str]
) -> None:
    chord, handler = expected
    assert DEFAULT_KEYMAP[command_id] == chord
    assert _lite()[handler] == chord, "one verb, two habits"


def test_say_selection_is_a_command_rather_than_a_key_handler_intercept() -> None:
    """It was reachable only as a conditional Shift+Space intercept.

    No chord, no menu row that could advertise one, nothing in the reference --
    so the command existed and could not be found (bad.md L12).
    """
    assert DEFAULT_KEYMAP["edit.say_selected"] == "Ctrl+Shift+Y"


# -- the two that needed a displacement ------------------------------------------


def test_horizontal_rule_stepped_aside_for_heading_navigation() -> None:
    """H is for Heading. Walking headings is an editing-loop verb; inserting a
    rule is a once-a-document one (bad.md rule 3)."""
    assert DEFAULT_KEYMAP["navigate.next_heading"] == "Ctrl+Alt+H"
    assert DEFAULT_KEYMAP["format.horizontal_rule"] == "Ctrl+Alt+-"


def test_copy_with_source_stepped_aside_for_describe_character() -> None:
    """ "What IS this symbol" is the question a listener asks constantly and a
    reader answers by looking; Copy With Source is a citation aid."""
    assert DEFAULT_KEYMAP["power.describe_character"] == "Ctrl+Shift+C"
    assert DEFAULT_KEYMAP["edit.copy_with_source"] == "Alt+Shift+C"


# -- rule 9: once a year, therefore on the F-keys ---------------------------------


@pytest.mark.parametrize(
    ("command_id", "handler", "chord"),
    (
        ("tools.individual_feature_toggles", "cmd_customize_features", "Ctrl+Alt+F10"),
        ("tools.share_export", "cmd_backup_settings", "Ctrl+Alt+F11"),
        ("tools.share_import", "cmd_restore_settings", "Ctrl+Alt+F12"),
    ),
)
def test_the_once_a_year_trio_agrees_and_left_the_letter_rows(
    command_id: str, handler: str, chord: str
) -> None:
    """They held Ctrl+Alt+Shift+F, Q and D in QuillLite -- three-modifier LETTER
    chords that editing verbs want in QUILL (Search in Files, Duplicate
    Selection). Nobody backs up their settings in the editing loop."""
    assert DEFAULT_KEYMAP[command_id] == chord
    assert _lite()[handler] == chord


# -- rule 5: a chord free in both is an alias, and nothing moves -------------------


@pytest.mark.parametrize(
    ("command_id", "chord"),
    (
        ("file.save_as", "F12"),
        ("file.open", "Ctrl+F12"),
        ("file.print", "Ctrl+Shift+F12"),
        ("help.key_cheatsheet", "Ctrl+F1"),
    ),
)
def test_words_function_keys_are_aliases_not_moves(command_id: str, chord: str) -> None:
    assert DEFAULT_ALIASES[command_id] == chord
    # The primary is untouched -- an alias is a second route, never a relocation.
    assert DEFAULT_KEYMAP[command_id] not in ("", chord)


def test_list_bookmarks_kept_every_chord_it_has_ever_had() -> None:
    """Three chords in three days, and not one of them dropped.

    ``navigate.list_bookmarks`` held ``Alt+Shift+B`` with ``Ctrl+Shift+F5`` --
    Word's own Bookmark key -- as an alias beside it. The whole-bar status
    switch took ``Alt+Shift+B`` (Notepad's chord for it, and QuillLite's) and
    the alias was promoted rather than replaced, which is the cheap shape of a
    move. Then rule 6 gave the command QuillLite's own ``Alt+Shift+G`` as the
    primary (bad.md P1.15), and Word's key went back to being the alias.

    Both of the earlier chords still reach it -- one as the live alias, one
    through ``legacy_rebindings`` -- which is the whole point. A person does not
    care which of the three they learned; they care that the one in their hands
    still opens the list.
    """
    assert DEFAULT_KEYMAP["navigate.list_bookmarks"] == "Alt+Shift+G"
    assert DEFAULT_ALIASES["navigate.list_bookmarks"] == "Ctrl+Shift+F5"


def test_the_shortcut_list_alias_is_quilllites_chord() -> None:
    assert DEFAULT_ALIASES["help.key_cheatsheet"] == _lite()["cmd_shortcuts"]


# -- the invariants that catch a bad move ----------------------------------------


def test_no_chord_is_claimed_by_two_commands() -> None:
    seen: dict[str, str] = {}
    for command_id, chord in DEFAULT_KEYMAP.items():
        if not chord:
            continue
        assert chord not in seen, f"{chord} is claimed by {seen[chord]} and {command_id}"
        seen[chord] = command_id


def test_no_alias_shadows_a_default_binding() -> None:
    defaults = {chord for chord in DEFAULT_KEYMAP.values() if chord}
    for command_id, chord in DEFAULT_ALIASES.items():
        assert chord not in defaults, f"alias {chord} for {command_id} shadows a real binding"


def test_quilllite_has_no_duplicate_chords_either() -> None:
    seen: dict[str, str] = {}
    for _m, _label, key, handler, _flag in COMMANDS:
        if not key:
            continue
        assert key not in seen, f"{key} is claimed by {seen[key]} and {handler}"
        seen[key] = handler

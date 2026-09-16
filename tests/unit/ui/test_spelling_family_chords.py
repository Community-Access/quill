"""The spelling family: one key meant two things, and one of them taught the dictionary.

``Alt+F7`` was Add Word to Dictionary in QuillLite and the word-level check in
QUILL. So the same reflex, in two editors that look and sound alike, either
looked a word up or taught a stored dictionary a word forever -- and the second
one is not undone by pressing the key again.

``Alt+F7`` is Next Misspelling in both now, which is what Word means by it and
is a command no habit can do damage with. Add Word moves off the F7 row
entirely, to ``Ctrl+Alt+F9``: that row is navigation, and the one command in
the family that writes to a stored dictionary should not sit where a spelling
habit can land on it.

Two other things fell out of making room, and both are improvements QUILL
needed anyway:

**Add Word became a real command.** It was reachable in QUILL only from the
context menu -- no command id, no key, no palette entry -- so a keyboard-only
user had to open a menu for the action they most often want after typing a
proper noun (bad.md 4.1).

**Ranked review became a checkbox.** Spell Check and Spell Check (Ranked by
Frequency) were one dialog opened two ways, on two chords, in two menu rows --
one verb registered twice (bad.md 7.1). The F7 chord family had no room for
the second once Alt+F7 changed hands, and the fold hands QuillLite ranked
review for the first time, because it shares the dialog and never had the
second command.
"""

from __future__ import annotations

import pytest

from quill.core.spelling.session import ReviewSession


def _lite_keys() -> dict[str, str]:
    from quill.core.lite.commands import COMMANDS

    return {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}


# -- the chords ------------------------------------------------------------------


def test_alt_f7_is_next_misspelling_in_both_and_teaches_nothing() -> None:
    from quill.core.keymap import DEFAULT_ALIASES
    from quill.core.lite.keymap import DEFAULT_ALIASES as LITE_ALIASES

    assert DEFAULT_ALIASES["tools.next_misspelling"] == "Alt+F7"
    assert LITE_ALIASES["cmd_next_misspelling"] == "Alt+F7"


def test_add_word_is_off_the_f7_row_in_both() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["tools.add_word_to_dictionary"] == "Ctrl+Alt+F9"
    assert _lite_keys()["cmd_add_word_to_dictionary"] == "Ctrl+Alt+F9"


def test_spelling_for_this_word_agrees_in_both() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["tools.spell_check_word_at_cursor"] == "Alt+Shift+F7"
    assert _lite_keys()["cmd_spell_word_at_cursor"] == "Alt+Shift+F7"


def test_shift_f7_stays_the_thesaurus_and_quilllite_leaves_it_alone() -> None:
    """QuillLite has no thesaurus, so the honest answer for the key is silence."""
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["tools.thesaurus"] == "Shift+F7"
    assert "Shift+F7" not in set(_lite_keys().values())


def test_the_whole_f7_family_agrees_between_the_editors() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    lite = _lite_keys()
    for command_id, handler in (
        ("tools.spell_check_dialog", "cmd_spell_review"),
        ("tools.next_misspelling", "cmd_next_misspelling"),
        ("tools.previous_misspelling", "cmd_previous_misspelling"),
        ("tools.spell_check_word_at_cursor", "cmd_spell_word_at_cursor"),
        ("tools.add_word_to_dictionary", "cmd_add_word_to_dictionary"),
    ):
        assert DEFAULT_KEYMAP[command_id] == lite[handler], (
            f"{command_id} and {handler} are one verb on two keys"
        )


# -- the retired command ---------------------------------------------------------


def test_ranked_spell_check_is_no_longer_a_second_command() -> None:
    from quill.core.feature_command_map import COMMAND_FEATURE_MAP
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.keymap_packs import _PACK_LABELS

    for table in (DEFAULT_KEYMAP, COMMAND_FEATURE_MAP, _PACK_LABELS):
        assert "tools.spell_check_ranked" not in table


def test_nothing_still_calls_the_retired_handler() -> None:
    from pathlib import Path

    for module in ("quill/ui/main_frame_menu_bindings.py", "quill/ui/main_frame_commands.py"):
        source = Path(module).read_text(encoding="utf-8")
        assert "spell_check_ranked" not in source, f"{module} still references it"


# -- the checkbox that replaced it, which both editors now share ------------------

TEXT = "teh cat sat on teh mat and teh dog watched. zzz once.\n"
DICTIONARY = {"cat", "sat", "on", "the", "mat", "and", "dog", "watched", "once"}


def _session(ranked: bool) -> ReviewSession:
    return ReviewSession(
        text=TEXT, dictionary=set(DICTIONARY), scope_start=0, scope_end=len(TEXT), ranked=ranked
    )


def test_ranked_order_puts_the_repeated_word_first() -> None:
    ranked = _session(ranked=True)
    current = ranked.current()
    assert current is not None
    assert current.word == "teh", "the word that recurs three times should be first"


def test_document_order_puts_the_first_word_first() -> None:
    plain = _session(ranked=False)
    current = plain.current()
    assert current is not None
    assert current.doc_start == TEXT.index("teh")


def test_toggling_mid_review_reorders_without_losing_progress() -> None:
    """The checkbox has to work while the dialog is open, not only at launch."""
    session = _session(ranked=False)
    before = session.total()
    session.apply_ignore_once()
    session.set_ranked(True)
    assert session.is_ranked() is True
    current = session.current()
    assert current is not None
    assert current.word == "teh"
    # The ignore survived the reorder: one issue fewer than we started with.
    assert session.total() == before - 1


def test_toggling_back_restores_document_order() -> None:
    session = _session(ranked=True)
    session.set_ranked(False)
    assert session.is_ranked() is False
    current = session.current()
    assert current is not None
    assert current.doc_start == TEXT.index("teh")


def test_setting_the_same_order_twice_is_a_no_op() -> None:
    session = _session(ranked=False)
    position = session.position()
    session.set_ranked(False)
    assert session.position() == position


# -- the setting both editors remember it in -------------------------------------


@pytest.mark.parametrize("module", ("quill.core.settings", "quill.core.lite.settings"))
def test_both_editors_remember_the_choice_under_the_same_name(module: str) -> None:
    """One name, so bad.md's grow-up path has one fewer row to map (G1)."""
    import dataclasses
    import importlib

    settings_cls = importlib.import_module(module).Settings
    names = {field.name for field in dataclasses.fields(settings_cls)}
    assert "spell_review_ranked" in names


def test_the_setting_is_documented_rather_than_grandfathered() -> None:
    from quill.core.settings_specs import SETTING_SPECS

    spec = next(s for s in SETTING_SPECS if s.key == "spell_review_ranked")
    assert spec.kind == "bool"
    assert spec.group == "spelling"
    assert "recurs" in spec.description.lower()
    assert "frequent" in spec.label.lower()

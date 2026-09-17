"""The settings-vocabulary gate (bad.md G1, §9 item 7).

The same concept spelled two ways is not a bug on its own. Together with the
same verb under two ids and the same announcement in two shapes, it is *the
mechanism* by which the two editors drift -- because there was nowhere a name
got decided once (bad.md 7.7). ``quill/core/lite/parity.py`` is that place, and
this is what keeps it honest.
"""

from __future__ import annotations

import dataclasses

from quill.core.lite.parity import NOT_ALIASES, SETTINGS_ALIASES, quill_setting_for
from quill.core.lite.settings import Settings as LiteSettings
from quill.core.settings import Settings as QuillSettings


def _lite_fields() -> set[str]:
    return {f.name for f in dataclasses.fields(LiteSettings)}


def _quill_fields() -> set[str]:
    return {f.name for f in dataclasses.fields(QuillSettings)}


def test_every_alias_names_a_field_that_exists_on_both_sides() -> None:
    """A mapping to a field nobody has is a mapping that silently does nothing,
    and "Bring my QuillLite settings" would drop that setting without a word."""
    lite, quill = _lite_fields(), _quill_fields()
    missing = [
        f"{left} -> {right}"
        for left, right in SETTINGS_ALIASES.items()
        if left not in lite or right not in quill
    ]
    assert missing == [], missing


def test_no_alias_maps_a_name_onto_itself() -> None:
    """Those three converged on one name; a row for them is noise that makes the
    table look like it has more disagreements in it than it does."""
    same = [left for left, right in SETTINGS_ALIASES.items() if left == right]
    assert same == [], same


def test_a_shared_name_needs_no_row() -> None:
    """Thirty-odd fields are spelled identically, and the resolver has to leave
    them alone rather than guess."""
    for field in sorted(_lite_fields() & _quill_fields()):
        if field in SETTINGS_ALIASES or field in NOT_ALIASES:
            continue
        assert quill_setting_for(field) == field


def test_the_four_known_pairs_resolve() -> None:
    assert quill_setting_for("autosave_seconds") == "autosave_interval_seconds"
    assert quill_setting_for("word_wrap") == "soft_wrap"
    assert quill_setting_for("spell_check_while_typing") == "spellcheck_as_you_type"
    assert quill_setting_for("default_mode") == "default_new_document_format"


def test_a_lookalike_pair_is_not_translated() -> None:
    """recent_files is QuillLite's LIST of files; recent_files_limit is QUILL's
    COUNT. Mapping one to the other hands an importer a list where it wants a
    number -- the one wrong answer that looks right."""
    assert quill_setting_for("recent_files") == "recent_files"


def test_a_field_nobody_has_heard_of_comes_back_unchanged() -> None:
    assert quill_setting_for("something_invented_in_a_test") == "something_invented_in_a_test"


def test_every_quilllite_field_is_either_shared_mapped_or_its_own() -> None:
    """The gate itself: a NEW QuillLite field whose concept already exists in
    QUILL under a different name has to be noticed here rather than discovered
    two releases later by somebody whose imported settings were half-applied.

    "Its own" is the common and legitimate case -- QuillLite has settings QUILL
    genuinely does not, and QUILL has three hundred it does not. What this
    catches is a field that is neither: spelled differently from QUILL's and not
    in the table.
    """
    lite, quill = _lite_fields(), _quill_fields()
    unexplained = sorted(
        field
        for field in lite - quill
        if field not in SETTINGS_ALIASES and field not in NOT_ALIASES
    )
    # Every name here is a QuillLite-only concept. Adding to this list is a
    # deliberate act: check first that QUILL does not already store the same
    # thing under another name, and if it does, add a row to SETTINGS_ALIASES
    # instead.
    quilllite_only = {
        # Notepad and WordPad both open one; QUILL opens a workspace, so the
        # question does not arise there in the same form.
        "open_blank_document_at_startup",
        # QUILL stores page setup in its own print model, not as three fields.
        "print_landscape",
        "print_margins_mm",
        "print_paper_id",
        # Session restore is QuillLite-only until G4 gives QUILL one.
        "restore_session",
        "session_files",
        # "Use QUILL's" only makes sense in the product that is not QUILL.
        "share_quill_abbreviations",
        "share_quill_dictionary",
        # The MDI shell remembers its own frame; QUILL's is the app shell's.
        "window_height",
        "window_maximized",
        "window_width",
    }
    assert set(unexplained) <= quilllite_only, sorted(set(unexplained) - quilllite_only)

"""Gate 4: the two editors must not name one idea two things.

The 2026-09 audit found five pairs of settings that are the same concept under
different names -- ``autosave_seconds`` / ``autosave_interval_seconds``,
``word_wrap`` / ``soft_wrap``, and three more. One of them,
``check_updates_on_launch`` / ``auto_check_updates``, had been missed by human
review twice, and the reason is instructive: **neither name contains a word the
other does**, so no amount of reading the two field lists side by side finds it.

Nor would a name-similarity gate: of the five real pairs, **two share no word at
all** (``spell_check_while_typing`` / ``spellcheck_as_you_type``,
``default_mode`` / ``default_new_document_format``), while "check", "print" and
"id" appear in dozens of unrelated fields on both sides. A heuristic over names
is simultaneously too loose and too tight to be the gate, which was worth
finding out before shipping one.

So the gate is a **ratchet on attention**, the shape GATE-SETDOC already proves
works: every field on either side is ``shared`` (same name), ``aliased`` (mapped
in ``SETTINGS_ALIASES`` or explicitly not a pair in ``NOT_ALIASES``), or
``one_side`` -- a reviewed judgement that the other product has no such concept.
A new field is ``missing`` and fails the build until somebody classifies it. The
machinery is :mod:`quill.tools.settings_vocabulary_audit`; what it enforces is
that nobody adds a setting without being made to ask the question.
"""

from __future__ import annotations

from quill.core.lite.parity import NOT_ALIASES, SETTINGS_ALIASES, quill_setting_for
from quill.core.lite.settings import Settings as LiteSettings
from quill.core.settings import Settings as QuillSettings

#: Every message here is a list read aloud, so each entry gets its own line.
NEWLINE_BULLET = "\n  "


def _fields(settings_class: type) -> set[str]:
    return {name for name in settings_class.__dataclass_fields__ if not name.startswith("_")}


def test_every_setting_on_either_side_has_been_looked_at() -> None:
    """The ratchet: a new field is unclassified until somebody asks the question."""
    from quill.tools.settings_vocabulary_audit import classify, missing

    unclassified = missing(classify())
    assert not unclassified, (
        "settings with no vocabulary verdict. Use the other product's name, add a "
        "row to SETTINGS_ALIASES / NOT_ALIASES, or classify it with "
        "python -m quill.tools.settings_vocabulary_audit --write:"
        + NEWLINE_BULLET
        + NEWLINE_BULLET.join(unclassified)
    )


def test_the_snapshot_matches_the_code() -> None:
    """A field that has since become shared or aliased must not stay one_side."""
    import json

    from quill.tools.settings_vocabulary_audit import SNAPSHOT_PATH, classify

    committed = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    live = classify(committed)
    drifted = sorted(
        f"{key}: snapshot says {committed.get(key)}, code says {state}"
        for key, state in live.items()
        if key in committed and committed[key] != state and state != "one_side"
    )
    assert not drifted, (
        "regenerate with python -m quill.tools.settings_vocabulary_audit --write:"
        + NEWLINE_BULLET
        + NEWLINE_BULLET.join(drifted)
    )
    gone = sorted(set(committed) - set(live))
    assert not gone, (
        "settings in the snapshot that no longer exist:"
        + NEWLINE_BULLET
        + NEWLINE_BULLET.join(gone)
    )


def test_every_alias_names_a_field_that_exists_on_both_sides() -> None:
    """A mapping to a field nobody has is a mapping an importer will act on."""
    lite_fields = _fields(LiteSettings)
    quill_fields = _fields(QuillSettings)
    broken: list[str] = []
    for lite_field, quill_field in sorted(SETTINGS_ALIASES.items()):
        if lite_field not in lite_fields:
            broken.append(f"{lite_field} is not a QuillLite setting")
        if quill_field not in quill_fields:
            broken.append(f"{quill_field} is not a QUILL setting")
    assert not broken, (
        "SETTINGS_ALIASES rows that name nothing:" + NEWLINE_BULLET + NEWLINE_BULLET.join(broken)
    )


def test_the_lookalikes_are_still_lookalikes() -> None:
    """If a NOT_ALIASES pair ever became the same concept, the row must go."""
    for lite_field, quill_field in sorted(NOT_ALIASES.items()):
        assert lite_field in _fields(LiteSettings), lite_field
        assert quill_field in _fields(QuillSettings), quill_field
        assert quill_setting_for(lite_field) == lite_field, (
            f"{lite_field} is in NOT_ALIASES but quill_setting_for translates it"
        )


def test_the_resolver_is_the_one_answer() -> None:
    """Every importer goes through it, so it must agree with the table."""
    for lite_field, quill_field in SETTINGS_ALIASES.items():
        assert quill_setting_for(lite_field) == quill_field
    assert quill_setting_for("a_field_nobody_has") == "a_field_nobody_has"


def test_the_gate_is_actually_comparing_something() -> None:
    """A gate that finds no fields on either side passes every rename ever made."""
    assert len(_fields(LiteSettings)) >= 40
    assert len(_fields(QuillSettings)) >= 200
    assert SETTINGS_ALIASES, "the alias table is empty; five pairs were found in 2026-09"

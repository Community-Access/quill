"""Where the two editors' vocabularies are written down, once.

The same concept is spelled two ways in several settings, the same verb has two
command ids, and the same announcement had two shapes. None of those is a bug on
its own; together they are **the mechanism by which the two editors drift**,
because there was no place where a name got decided once (bad.md 7.7).

This module is that place. Today it holds the **settings** half:
:data:`SETTINGS_ALIASES` maps QuillLite's field name to QUILL's, for every
concept both products store under different names (bad.md G1). It is what
"Bring my QuillLite settings" reads when somebody grows up into QUILL (5.8),
and what the settings-vocabulary gate checks a new field against.

The **command** half belongs here too and is not written yet: the family parity
gate (§9 item 1, bad.md P1.15) needs a QuillLite-handler-to-QUILL-command-id
table so the two can be asserted to resolve to the same chord. The mapping
exists today inside ``tests/unit/core/lite/test_lite_selection.py``, covering
the selection family only; moving it here and completing it is P1.15's job, and
:data:`DIVERGENCES` is waiting for it.

**Why a mapping and not a rename.** Both tables could be emptied by renaming
one side, and both sides' names are already on disk in people's settings files
and keymap overrides. A rename is a migration for every existing user, in
exchange for a tidiness nobody can see. The mapping costs one row and is
checkable, which is the thing the rename was supposed to buy.

**The table is the review.** A new shared concept that lands under a second
name fails the gate until somebody either picks the existing name or writes the
row -- and writing the row is where they have to say, in words, why two names
are right.
"""

from __future__ import annotations

__all__ = ["DIVERGENCES", "SETTINGS_ALIASES", "quill_setting_for"]

#: QuillLite's field name -> QUILL's, for one concept stored under two names.
#:
#: Five rows, and each one is a concept a person would describe with the same
#: sentence in either product (bad.md G1). Three more pairs the audit named have
#: since converged on one name and are deliberately absent: ``font_name``,
#: ``font_size`` and ``show_status_bar`` are spelled identically in both.
SETTINGS_ALIASES: dict[str, str] = {
    # "How often it saves a copy of unsaved work." QuillLite's name is the
    # shorter and the clearer of the two; QUILL's says "interval" twice.
    "autosave_seconds": "autosave_interval_seconds",
    # "Whether long lines wrap to the window." Notepad, WordPad and Word all
    # call this Word Wrap, which is QuillLite's name and the one the menus in
    # both products show -- QUILL's field is the outlier, not its label.
    "word_wrap": "soft_wrap",
    # "Whether it checks spelling as you type."
    "spell_check_while_typing": "spellcheck_as_you_type",
    # "What kind of document a new one is." Not quite the same shape -- Lite's
    # is plain/rich, QUILL's names a format -- which is why 5.8's importer has
    # to translate rather than copy, and why this row exists.
    "default_mode": "default_new_document_format",
    # "Whether it looks for a new version by itself." A fifth pair the G1 audit
    # missed, found by this table's own gate on 2026-09-17: neither name
    # contains a word the other does, so no amount of eyeballing the two field
    # lists finds it. That is the argument for the gate.
    "check_updates_on_launch": "auto_check_updates",
}

#: Pairs that look like the same concept and are not, recorded so nobody adds
#: them to the table above by pattern-matching on the name.
#:
#: ``recent_files`` / ``recent_files_limit`` is the one that catches people:
#: QuillLite's is **the list of files** and QUILL's is **how many to keep**. A
#: mapping between them would hand an importer a list where it expected a
#: number.
NOT_ALIASES: dict[str, str] = {
    "recent_files": "recent_files_limit",
}

#: Command pairs allowed to resolve to different chords, each with its reason.
#:
#: Empty, and the emptiness is the point: every divergence the family audit
#: found has either been resolved or is still open in the plan. A row here is a
#: promise that somebody thought about it, not a place to park a collision.
DIVERGENCES: dict[str, str] = {}


def quill_setting_for(lite_field: str) -> str:
    """QUILL's name for *lite_field*, or *lite_field* when they agree.

    Never raises, and never guesses: a field this table has never heard of is
    returned unchanged, which is correct for the thirty-odd names the two
    products already spell identically.
    """
    if lite_field in NOT_ALIASES:
        # Same-looking, different thing. Returning QUILL's name here would be
        # the one wrong answer that looks right.
        return lite_field
    return SETTINGS_ALIASES.get(lite_field, lite_field)

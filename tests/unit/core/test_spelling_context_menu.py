"""What a right-click on a misspelled word offers, and what "ignore" means.

The menu itself is wx and lives in two apps; every decision it makes is here,
so both can be held to the same answers without a display.
"""

from __future__ import annotations

from quill.core.spellcheck import Misspelling, list_misspellings
from quill.core.spelling.context_menu import IgnoreList, spelling_context

DICTIONARY: set[str] = set()


def _at(text: str, word: str) -> Misspelling:
    start = text.index(word)
    return Misspelling(word=word, start=start, end=start + len(word))


# ---------------------------------------------------------------------------
# The context itself


def test_a_misspelling_at_the_caret_comes_back_with_suggestions() -> None:
    text = "the wrold is round"
    context = spelling_context(text, text.index("wrold") + 2, DICTIONARY)
    assert context is not None
    assert context.word == "wrold"
    assert context.suggestions


def test_a_correctly_spelled_word_is_no_context_at_all() -> None:
    """None, so the caller builds a menu with no spelling section rather than
    one with a disabled row every right-click makes somebody arrow past."""
    text = "the world is round"
    assert spelling_context(text, 6, DICTIONARY) is None


def test_the_suggestion_count_is_the_callers_to_cap() -> None:
    text = "the wrold is round"
    context = spelling_context(text, text.index("wrold"), DICTIONARY, limit=2)
    assert context is not None
    assert len(context.suggestions) <= 2


# ---------------------------------------------------------------------------
# Ignore in this document


def test_an_ignored_word_is_not_a_misspelling_here_any_more() -> None:
    """Offering "ignore" for a word already ignored is a row that does nothing."""
    text = "the wrold is round"
    ignores = IgnoreList()
    ignores.ignore_word("wrold")
    assert spelling_context(text, text.index("wrold"), DICTIONARY, ignores) is None


def test_ignoring_a_word_ignores_every_case_of_it() -> None:
    """Somebody ignoring a surname at the top of a letter meant the one in the
    signature too, whatever either of them is capitalised as."""
    ignores = IgnoreList()
    ignores.ignore_word("Wrold")
    text = "wrold and WROLD"
    assert ignores.skips(text, _at(text, "wrold"))
    assert ignores.skips(text, _at(text, "WROLD"))


def test_ignoring_one_word_leaves_the_others_alone() -> None:
    text = "wrold and teh"
    ignores = IgnoreList()
    ignores.ignore_word("wrold")
    assert not ignores.skips(text, _at(text, "teh"))


# ---------------------------------------------------------------------------
# Ignore once


def test_ignore_once_skips_that_occurrence_and_no_other() -> None:
    text = "wrold and wrold"
    ignores = IgnoreList()
    first = Misspelling("wrold", 0, 5)
    second = Misspelling("wrold", 10, 15)
    ignores.ignore_once(first)
    assert ignores.skips(text, first)
    assert not ignores.skips(text, second)


def test_ignore_once_survives_an_edit_somewhere_else() -> None:
    """The occurrence has not moved, so the suppression still applies -- this is
    what makes the anchor worth having rather than clearing on every keystroke.
    """
    ignores = IgnoreList()
    item = Misspelling("wrold", 0, 5)
    ignores.ignore_once(item)
    assert ignores.skips("wrold is round indeed", item)


def test_ignore_once_lets_go_when_the_text_there_is_something_else() -> None:
    """Self-cleaning rather than shifted: an offset that no longer spells the
    ignored word is a different word, and suppressing it would hide a real one.
    """
    ignores = IgnoreList()
    item = Misspelling("wrold", 6, 11)
    ignores.ignore_once(item)
    assert not ignores.skips("hello teh    is round", item)
    assert not ignores.once  # and the stale anchor is gone, not merely inert


def test_survivors_filters_a_whole_list_in_order() -> None:
    text = "wrold and teh and wrold"
    ignores = IgnoreList()
    ignores.ignore_word("teh")
    found = list_misspellings(text, DICTIONARY)
    kept = ignores.survivors(text, found)
    assert [item.word for item in kept] == ["wrold", "wrold"]


def test_clear_puts_everything_back() -> None:
    ignores = IgnoreList()
    ignores.ignore_word("wrold")
    ignores.ignore_once(Misspelling("teh", 0, 3))
    ignores.clear()
    assert not ignores.words
    assert not ignores.once


def test_the_caret_just_past_the_last_letter_still_counts_as_in_the_word() -> None:
    """Where the caret is the instant somebody finishes typing a word and
    reaches for the Applications key -- which "which word am I on" calls
    outside it, and a context menu has to call inside."""
    text = "the wrold is round"
    context = spelling_context(text, text.index("wrold") + len("wrold"), DICTIONARY)
    assert context is not None
    assert context.word == "wrold"


def test_the_fallback_cannot_invent_a_misspelling_after_a_good_word() -> None:
    text = "the world is round"
    assert spelling_context(text, len("the world"), DICTIONARY) is None

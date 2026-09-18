"""Spelling parity into QUILL (bad.md S4, S5, P1.14).

Two of these are the same bug wearing different clothes: the checker did not
agree with itself about what a word is, or about where one ends.

S4: the tokenizer was ASCII (`[A-Za-z]`) and the walk-left beside it was
Unicode (`str.isalpha()`), so `café` was flagged as `caf`, `naïve` as `na` and
`ve`, and a curly apostrophe split `don't` in two -- and the same word was
silent on one path and flagged on another.

S5: the caret sits at the *end* of the word you have just typed, and the lookup
required `start <= position < end`, so "what is the word under the cursor?"
answered "there is no word" at the one moment people most often ask. Two
context menus retried at `position - 1`; the four keyboard commands did not.
"""

from __future__ import annotations

from quill.core.spellcheck import (
    _WORD_PATTERN,
    misspelling_at_position,
    misspelling_behind,
)

DICTIONARY = {"the", "word", "cafe", "naive", "dont", "hello"}
CURLY = "’"


def _tokens(text: str) -> list[str]:
    return [match.group(0) for match in _WORD_PATTERN.finditer(text)]


def test_an_accented_word_is_one_word() -> None:
    assert _tokens("café") == ["café"]


def test_a_diaeresis_does_not_split_a_word_in_two() -> None:
    assert _tokens("naïve") == ["naïve"]


def test_a_typographic_apostrophe_holds_a_contraction_together() -> None:
    """The one every word processor inserts for you, including this one."""
    assert _tokens("don" + CURLY + "t") == ["don" + CURLY + "t"]
    assert _tokens("don't") == ["don't"]


def test_the_ordinal_guard_still_holds() -> None:
    """Letters straight after digits are not words: 3D, 1080p, 500ml, 12pt."""
    assert "3D" not in _tokens("a 3D model")
    assert "1080p" not in _tokens("1080p video")


def test_the_pattern_and_the_walk_agree_about_what_a_word_is() -> None:
    """The actual S4 defect: two halves of one checker with two definitions."""
    from quill.core.spellcheck import _is_word_character

    for character in "cafénaïve" + CURLY + "'":
        assert _is_word_character(character), character
    assert _tokens("café naïve") == ["café", "naïve"]


def test_the_caret_just_past_a_word_finds_that_word() -> None:
    """Where the caret is after typing it, which is when people ask."""
    text = "the wrng"
    assert misspelling_at_position(text, len(text), DICTIONARY) is not None


def test_the_caret_inside_a_word_still_finds_it() -> None:
    assert misspelling_at_position("the wrng", 5, DICTIONARY) is not None


def test_a_correctly_spelled_word_is_not_reported_either_way() -> None:
    assert misspelling_at_position("the word", 8, DICTIONARY) is None
    assert misspelling_at_position("the word", 6, DICTIONARY) is None


def test_the_caret_in_open_space_reports_nothing() -> None:
    """Two spaces after the word: no word is being asked about."""
    assert misspelling_at_position("the wrng  ", 10, DICTIONARY) is None


def test_an_accented_misspelling_is_reported_whole() -> None:
    found = misspelling_at_position("caféx here", 5, DICTIONARY)
    assert found is not None
    assert found.word == "caféx"


def test_the_just_finished_word_agrees_with_the_new_tokenizer() -> None:
    """The as-you-type path reads the same tokens as the review path now."""
    # The caret is past the terminating space: this is the word just finished.
    found = misspelling_behind("a caféx ", 8, DICTIONARY)
    assert found is not None
    assert found.word == "caféx"

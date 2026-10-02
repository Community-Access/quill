"""The word under the caret, walked back to a headword and its synonyms walked forward.

Most of these use a small fake thesaurus so they pin the rules rather than the
contents of an 18 MB data file; the last few touch the real file, skipped when
it is absent, because "running" finding "sprinting" is the whole point.
"""

from __future__ import annotations

import pytest

from quill.core import thesaurus
from quill.core.thesaurus import Meaning, ThesaurusEntry
from quill.core.word_lookup import (
    COMPARATIVE,
    ING,
    PAST,
    PLAIN,
    PLURAL,
    SUPERLATIVE,
    THIRD,
    WordSpan,
    find_word,
    inflect,
    is_single_word,
    lemma_candidates,
    match_case,
    sentence_around,
    thesaurus_choices,
)

# -- finding the word ------------------------------------------------------------------


def test_the_caret_word_is_found_inside_after_and_never_in_a_space() -> None:
    text = "The quick fox."
    assert find_word(text, 5) == WordSpan("quick", 4, 9)
    assert find_word(text, 9) == WordSpan("quick", 4, 9)  # just after the word
    assert find_word("a  b", 2) is None


def test_a_one_word_selection_wins_and_a_sentence_does_not() -> None:
    text = "Read the well-known book."
    assert find_word(text, 0, (9, 19)) == WordSpan("well-known", 9, 19)
    assert find_word(text, 2, (0, 13)) == WordSpan("Read", 0, 4)  # not a word: caret's


def test_quotes_are_not_part_of_the_word() -> None:
    text = "She said 'hello' twice."
    assert find_word(text, 12) == WordSpan("hello", 10, 15)


def test_single_words() -> None:
    assert is_single_word("don't") and is_single_word("well-known")
    assert not is_single_word("two words") and not is_single_word("42")


def test_the_sentence_around_a_word_is_only_that_sentence() -> None:
    text = "First one. The river bank was steep! Third."
    start = text.index("bank")
    assert sentence_around(text, start, start + 4) == "The river bank was steep!"


# -- capitals and inflection -------------------------------------------------------------


@pytest.mark.parametrize(
    ("original", "replacement", "expected"),
    [("Quick", "fast", "Fast"), ("QUICK", "fast", "FAST"), ("quick", "fast", "fast")],
)
def test_match_case(original: str, replacement: str, expected: str) -> None:
    assert match_case(original, replacement) == expected


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("running", ("run", ING)),
        ("making", ("make", ING)),
        ("lying", ("lie", ING)),
        ("stopped", ("stop", PAST)),
        ("baked", ("bake", PAST)),
        ("carried", ("carry", PAST)),
        ("ran", ("run", PAST)),
        ("studies", ("study", PLURAL)),
        ("boxes", ("box", PLURAL)),
        ("happier", ("happy", COMPARATIVE)),
        ("biggest", ("big", SUPERLATIVE)),
    ],
)
def test_walking_back_reaches_the_headword(word: str, expected: tuple[str, str]) -> None:
    assert expected in lemma_candidates(word)
    assert lemma_candidates(word)[0] == (word, PLAIN)


@pytest.mark.parametrize(
    ("term", "how", "expected"),
    [
        ("sprint", ING, "sprinting"),
        ("hop", ING, "hopping"),
        ("bake", ING, "baking"),
        ("tie", ING, "tying"),
        ("halt", PAST, "halted"),
        ("hurry", PAST, "hurried"),
        ("give up", PAST, "gave up"),  # irregular, and a phrase: the verb moves
        ("seek", PAST, "sought"),
        ("survey", PLURAL, "surveys"),
        ("box", PLURAL, "boxes"),
        ("ice cream", PLURAL, "ice creams"),
        ("go", THIRD, "goes"),
        ("large", COMPARATIVE, "larger"),
        ("big", SUPERLATIVE, "biggest"),
        ("happy", COMPARATIVE, "happier"),
        ("blessed", COMPARATIVE, "more blessed"),  # never "blesseder"
        ("beautiful", SUPERLATIVE, "most beautiful"),
    ],
)
def test_walking_forward_gives_a_usable_word(term: str, how: str, expected: str) -> None:
    assert inflect(term, how) == expected


# -- choices, with a fake thesaurus ------------------------------------------------------


def _fake(entries: dict[str, ThesaurusEntry]):
    return lambda word: entries.get(word)


FAKE = {
    "run": ThesaurusEntry(
        "run",
        (
            Meaning("verb", ("sprint", "dash", "run")),
            Meaning("noun", ("tally", "score")),
        ),
    ),
    "running": ThesaurusEntry("running", (Meaning("adj", ("operative",), ("idle",)),)),
    "quick": ThesaurusEntry("quick", (Meaning("adj", ("fast", "speedy"), ("slow",)),)),
}


def test_the_verb_behind_an_ing_word_comes_first_and_is_inflected() -> None:
    choices = thesaurus_choices("Running", lookup=_fake(FAKE))
    assert choices is not None
    assert choices.headword == "run" and choices.how == ING
    first = choices.senses[0]
    assert first.label == "As a verb: sprint"
    assert first.replacements == ("Sprinting", "Dashing")  # the headword itself left out
    # The noun sense of "run" is not offered for "running"...
    assert all(sense.part_of_speech != "noun" for sense in choices.senses)
    # ...but the word's own adjective sense still is, after the verb.
    assert choices.senses[1].replacements == ("Operative",)
    assert choices.opposites == ("Idle",)


def test_opposites_are_kept_apart_and_a_summary_says_how_much() -> None:
    choices = thesaurus_choices("quick", lookup=_fake(FAKE))
    assert choices is not None
    assert choices.all_replacements == ("fast", "speedy")
    assert choices.opposites == ("slow",)
    assert choices.summary() == "quick: 1 meaning, 2 replacements."


def test_an_unknown_word_has_no_choices() -> None:
    assert thesaurus_choices("zzyzx", lookup=_fake(FAKE)) is None
    assert thesaurus_choices("  ", lookup=_fake(FAKE)) is None


# -- the real file -------------------------------------------------------------------------

needs_data = pytest.mark.skipif(not thesaurus.is_available(), reason="thesaurus data absent")


@needs_data
def test_running_offers_running_words_from_the_real_thesaurus() -> None:
    choices = thesaurus_choices("running")
    assert choices is not None and choices.headword == "run"
    assert all(" " in term or term.endswith("ing") for term in choices.senses[0].replacements)


@needs_data
def test_stopped_offers_past_tense_words_including_irregular_ones() -> None:
    choices = thesaurus_choices("stopped")
    assert choices is not None
    replacements = choices.all_replacements
    assert "halted" in replacements and "gived up" not in replacements


# -- the picker, by headword, and the spoken summary (2026-10-02) --------------------


def test_the_picker_reaches_the_verb_behind_running_and_inflects_every_row() -> None:
    from quill.core.word_lookup import picker_senses

    headword, how, senses = picker_senses("running")

    assert (headword, how) == ("run", "ing")
    assert senses, "run has senses"
    first = senses[0]
    assert first.label.startswith("verb, from run:")
    assert first.part_of_speech == "verb"
    # Every row is a usable replacement in the sentence's form, label and term alike.
    for label, term in first.rows:
        assert term.endswith("ing") or " " in term, (label, term)
    assert any(label.startswith("opposite: ") for sense in senses for label, _t in sense.rows)


def test_the_picker_keeps_the_original_capitals_and_the_own_word_last() -> None:
    from quill.core.word_lookup import picker_senses

    headword, how, senses = picker_senses("Happier")

    assert (headword, how) == ("happy", "er")
    assert senses[0].rows[0][1][0].isupper()
    # "happier" itself is not a headword; every sense came through "happy".
    assert all("from happy" in sense.label for sense in senses)


def test_an_unknown_word_has_no_picker_senses() -> None:
    from quill.core.word_lookup import picker_senses

    assert picker_senses("zzqxv") == ("zzqxv", "", ())
    assert picker_senses("   ") == ("", "", ())


def test_the_summary_says_the_headword_the_counts_and_the_opposites() -> None:
    from quill.core.word_lookup import word_summary

    said = word_summary("running")

    assert said.startswith("running, looked up as run: ")
    assert "meanings as a verb" in said
    assert "First: " in said
    assert "Opposites: " in said


def test_the_summary_for_an_unknown_word_is_one_plain_sentence() -> None:
    from quill.core.word_lookup import word_summary

    assert word_summary("zzqxv") == "The thesaurus has no entry for zzqxv."

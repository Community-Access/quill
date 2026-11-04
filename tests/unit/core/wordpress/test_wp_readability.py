"""Local reading level (quill.core.wordpress.readability)."""

from __future__ import annotations

import pytest

from quill.core.wordpress.readability import (
    ReadingLevel,
    count_syllables,
    describe,
    reading_level,
    strip_html,
)

# -- syllables ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("word", "count"),
    [
        ("cat", 1),
        ("the", 1),
        ("table", 2),
        ("make", 1),
        ("water", 2),
        ("beautiful", 3),
        ("education", 4),
        ("jumped", 1),
        ("wanted", 2),
        ("boxes", 2),
        ("wishes", 2),
        ("rhythm", 1),
        ("don't", 1),
        ("a", 1),
        ("", 0),
    ],
)
def test_count_syllables(word: str, count: int) -> None:
    assert count_syllables(word) == count


# -- stripping HTML -----------------------------------------------------------------


def test_strip_html_removes_tags_and_block_comments() -> None:
    html = "<!-- wp:paragraph --><p>Hello <strong>world</strong>.</p><!-- /wp:paragraph -->"
    assert strip_html(html).text.strip() == "Hello world."


def test_strip_html_decodes_entities() -> None:
    assert strip_html("<p>Fish &amp; chips &#8212; &copy;</p>").text.strip() == ("Fish & chips — ©")


def test_strip_html_drops_script_and_style() -> None:
    plain = strip_html("<style>p{}</style><p>Hi.</p><script>var x = 1;</script>")
    assert plain.text.strip() == "Hi."


def test_strip_html_breaks_blocks() -> None:
    text = strip_html("<h2>Title</h2><p>Body</p>").text
    assert "Title\nBody" in text


def test_strip_html_offsets_point_into_source() -> None:
    html = "<p>ab <em>cd</em></p>"
    plain = strip_html(html)
    index = plain.text.index("cd")
    assert plain.source_offset(index) == html.index("cd")


def test_source_offset_clamps() -> None:
    plain = strip_html("<p>x</p>")
    assert plain.source_offset(999) == plain.source_offsets[-1]
    assert strip_html("").source_offset(3) == 0


# -- reading level ------------------------------------------------------------------


def test_simple_text_is_low_grade() -> None:
    level = reading_level("The cat sat on the mat. The dog ran to the park.")
    assert level.words == 12
    assert level.sentences == 2
    assert level.words_per_sentence == 6
    assert level.grade < 2


def test_known_flesch_kincaid_value() -> None:
    # 10 words, 1 sentence, 16 syllables: 0.39*10 + 11.8*1.6 - 15.59 = 7.19
    text = "Reading is a habit that rewards patient people over time."
    level = reading_level(text)
    assert level.words == 10
    assert level.syllables == 16
    assert level.grade == pytest.approx(0.39 * 10 + 11.8 * 1.6 - 15.59)


def test_complex_text_is_higher_grade() -> None:
    simple = reading_level("We like to play. It is fun. We go out.")
    hard = reading_level(
        "Comprehensive institutional accountability necessitates continuous "
        "evaluation of organisational effectiveness, particularly regarding "
        "administrative responsibilities and interdepartmental communication."
    )
    assert hard.grade > simple.grade + 10


def test_longest_sentences_with_offsets() -> None:
    text = "Short one. This sentence is clearly the longest of them all. Mid size here now."
    level = reading_level(text)
    longest = level.longest
    assert longest[0].text == "This sentence is clearly the longest of them all."
    assert longest[0].word_count == 9
    assert longest[0].offset == text.index("This")
    assert [s.word_count for s in longest] == [9, 4, 2]


def test_longest_is_capped_at_three() -> None:
    level = reading_level("One. Two two. Three three three. Four four four four.")
    assert len(level.longest) == 3


def test_question_and_exclamation_end_sentences() -> None:
    assert reading_level("Is it here? Yes! It is.").sentences == 3


def test_decimal_and_abbreviation_inside_sentence() -> None:
    # "3.5" is not a sentence break: no space after the full stop.
    assert reading_level("It costs 3.5 dollars today.").sentences == 1


def test_html_input_offsets_map_to_html() -> None:
    html = (
        "<!-- wp:heading --><h2>Our plan</h2><!-- /wp:heading -->"
        "<!-- wp:paragraph --><p>We will build a garden behind the old library this "
        "spring.</p><!-- /wp:paragraph -->"
    )
    level = reading_level(html, is_html=True)
    assert level.sentences == 2  # the heading is its own sentence
    first = level.longest[0]
    assert first.text.startswith("We will build")
    assert first.offset == html.index("We will build")


def test_empty_text() -> None:
    level = reading_level("   ")
    assert level == ReadingLevel(0.0, 0, 0, 0, 0.0, ())
    assert reading_level("<p></p>", is_html=True).words == 0


# -- describe -----------------------------------------------------------------------


def _level(grade: float, per: float) -> ReadingLevel:
    return ReadingLevel(grade, 10, 1, 10, per, ())


@pytest.mark.parametrize(
    ("grade", "per", "expected"),
    [
        (9.2, 14.0, "Reading level: about 9th grade, 14 words per sentence"),
        (1.0, 6.0, "Reading level: about 1st grade, 6 words per sentence"),
        (-2.0, 3.0, "Reading level: about 1st grade, 3 words per sentence"),
        (2.0, 8.0, "Reading level: about 2nd grade, 8 words per sentence"),
        (3.4, 9.0, "Reading level: about 3rd grade, 9 words per sentence"),
        (11.0, 20.0, "Reading level: about 11th grade, 20 words per sentence"),
        (12.4, 22.0, "Reading level: about 12th grade, 22 words per sentence"),
        (15.0, 30.0, "Reading level: college level, 30 words per sentence"),
        (1.0, 1.0, "Reading level: about 1st grade, 1 word per sentence"),
    ],
)
def test_describe(grade: float, per: float, expected: str) -> None:
    assert describe(_level(grade, per)) == expected


def test_describe_no_text() -> None:
    assert describe(reading_level("")) == "Reading level: not enough text to judge"

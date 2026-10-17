"""The readability score the PDF reader chooses pages by (quill.io.pdf_score).

The old score rewarded quantity: characters, words, pages. These tests pin the
replacement -- bounded, damage-driven, and fair to text that is short, numeric
or not in English.
"""

from __future__ import annotations

import random

from quill.io.pdf_score import (
    DOUBTFUL_PAGE_SCORE,
    FAST_PATH_SCORE,
    content_chars,
    readability,
    score_text,
    unreadable_count,
)

_PROSE = (
    "The committee met on a Tuesday, which was unusual, and agreed that the report "
    "would be circulated before the end of the month. Nobody objected to the timetable."
)


def test_repeated_replacement_characters_never_score_100() -> None:
    assert score_text("�" * 200) == 0
    assert score_text("��� ��") == 0
    # Even a minority of junk costs: a fifth of the page is unreadable.
    assert score_text(_PROSE + " " + "�" * 40) < FAST_PATH_SCORE


def test_clean_prose_scores_100() -> None:
    assert score_text(_PROSE) == 100


def test_a_short_title_numbers_and_other_scripts_are_not_penalized() -> None:
    assert score_text("Chapter One") == 100
    assert score_text("1,250   18.75   23,437.50\n980   18.75   18,375.00") == 100
    assert score_text("Η επιτροπή συνεδρίασε την Τρίτη και συμφώνησε.") == 100
    assert score_text("委員会は火曜日に開かれ、報告書を月末までに配布することに合意した。") == 100
    assert score_text("Комитет собрался во вторник и согласился с отчётом.") == 100
    assert score_text("2024") == 100


def test_letters_one_at_a_time_score_low() -> None:
    spaced = "T h e c o m m i t t e e m e t o n a T u e s d a y"
    assert score_text(spaced) < DOUBTFUL_PAGE_SCORE
    assert readability(spaced).fragmented < 0.5


def test_one_word_per_line_scores_lower_than_the_same_words_as_prose() -> None:
    one_per_line = "\n".join(_PROSE.split())
    assert score_text(one_per_line) < score_text(_PROSE)
    assert score_text(one_per_line) >= 40  # a soft factor: never below 0.4


def test_implausible_joins_score_low() -> None:
    joined = "Widelettersarehardtoread wheneveryonestandsalone everyletterruntogether"
    assert score_text(joined) <= 20
    assert score_text("HHeelllloo wwoorrlldd ffrroomm hheerree") < DOUBTFUL_PAGE_SCORE
    assert score_text("the end of the figures.The next sentence startedHere today") < 100


def test_a_few_long_words_and_product_names_are_allowed() -> None:
    text = _PROSE + " The PowerPoint deck and the Bundesverfassungsgericht ruling were noted."
    assert score_text(text) >= FAST_PATH_SCORE


def test_coverage_counts_against_a_reading_that_lost_content() -> None:
    full = content_chars(_PROSE)
    half = _PROSE[: len(_PROSE) // 2]
    assert score_text(half, reference_chars=full) < 60
    assert score_text(_PROSE, reference_chars=full) == 100


def test_columns_run_together_cost_the_reading_that_ran_them() -> None:
    rows = [
        ("The river rose slowly", "Repairs will begin soon"),
        ("and by morning", "once the survey ends"),
    ]
    interleaved = (
        "The river rose slowly Repairs will begin soon\nand by morning once the survey ends"
    )
    in_order = (
        "The river rose slowly\nand by morning\nRepairs will begin soon\nonce the survey ends"
    )
    assert readability(interleaved, column_rows=rows).score == 50
    assert readability(in_order, column_rows=rows).score == 100


def test_private_use_and_cid_placeholders_are_unreadable() -> None:
    assert unreadable_count("net bo") == 2
    assert unreadable_count("(cid:12)(cid:7) text") == 2
    assert unreadable_count(_PROSE) == 0
    assert score_text("(cid:12)" * 30) == 0


def test_empty_text_scores_zero() -> None:
    assert score_text("") == 0
    assert score_text("   \n\f ") == 0


def test_the_score_is_always_between_0_and_100() -> None:
    rng = random.Random(28)
    alphabet = "ab cDE\n� 1.,\fxyzQ  "
    for _ in range(300):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 200)))
        reference = rng.choice([None, 1, 50, 500])
        assert 0 <= score_text(text, reference_chars=reference) <= 100


def test_the_thresholds_are_ordered() -> None:
    assert 0 < DOUBTFUL_PAGE_SCORE < FAST_PATH_SCORE <= 100

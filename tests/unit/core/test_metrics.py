from quill.core.metrics import (
    LONG_SENTENCE_WORDS,
    RepeatPress,
    compute_document_stats,
    compute_writing_stats,
    count_paragraphs,
    describe_writing_stats,
    reading_minutes,
    statistics_report,
)
from quill.core.readability import flesch_kincaid_grade, grade_phrase


def test_compute_document_stats_for_empty_text() -> None:
    stats = compute_document_stats("")
    assert stats.words == 0
    assert stats.lines == 0
    assert stats.characters == 0


def test_compute_document_stats_for_multiline_text() -> None:
    stats = compute_document_stats("hello world\nsecond line")
    assert stats.words == 4
    assert stats.lines == 2
    assert stats.characters == len("hello world\nsecond line")


# --------------------------------------------------------------------------- #
# The writing statistics a second press adds
# --------------------------------------------------------------------------- #


def test_paragraphs_are_blank_line_blocks_when_the_text_uses_blank_lines() -> None:
    text = "One line\nstill the first.\n\nSecond paragraph.\n\n\nThird.\n"
    assert count_paragraphs(text) == 3


def test_paragraphs_are_lines_when_the_text_never_leaves_a_blank_line() -> None:
    assert count_paragraphs("First.\nSecond.\nThird.") == 3


def test_paragraphs_of_nothing_is_zero() -> None:
    assert count_paragraphs("") == 0
    assert count_paragraphs("\n  \n") == 0


def test_paragraphs_count_windows_line_endings_too() -> None:
    assert count_paragraphs("A.\r\n\r\nB.\r\n") == 2


def test_sentences_and_long_sentences() -> None:
    long_one = " ".join(["word"] * (LONG_SENTENCE_WORDS + 1)) + "."
    exactly = " ".join(["word"] * LONG_SENTENCE_WORDS) + "."
    text = f"Short one. Another short one! {long_one} {exactly} Is this a question?"
    stats = compute_writing_stats(text)
    assert stats.sentences == 5
    # Over thirty words is long; exactly thirty is not.
    assert stats.long_sentences == 1


def test_grade_matches_the_flesch_kincaid_formula() -> None:
    # "The cat sat." -> 3 words, 1 sentence, 3 syllables.
    stats = compute_writing_stats("The cat sat.")
    assert stats.grade is not None
    assert abs(stats.grade - (0.39 * 3 + 11.8 * 1 - 15.59)) < 1e-9
    assert flesch_kincaid_grade(3, 1, 3) == stats.grade


def test_harder_text_has_a_higher_grade() -> None:
    easy = compute_writing_stats("The dog ran. The cat sat. We had fun.")
    hard = compute_writing_stats(
        "Comprehensive institutional documentation necessitates considerable "
        "organizational deliberation regarding interdepartmental responsibilities."
    )
    assert easy.grade is not None and hard.grade is not None
    assert hard.grade > easy.grade + 5


def test_no_text_has_no_grade() -> None:
    stats = compute_writing_stats("   \n")
    assert stats.grade is None
    assert stats.sentences == 0
    assert stats.reading_minutes == 0


def test_grade_phrase() -> None:
    assert grade_phrase(8.6) == "about 9th grade"
    assert grade_phrase(-3.0) == "about 1st grade"
    assert grade_phrase(12.4) == "about 12th grade"
    assert grade_phrase(15.0) == "college level"


def test_reading_minutes_round_up_at_the_status_bar_speed() -> None:
    assert reading_minutes(0) == 0
    assert reading_minutes(1) == 1
    assert reading_minutes(200) == 1
    assert reading_minutes(201) == 2


def test_the_long_report_says_every_number() -> None:
    text = "First paragraph here.\n\n" + ("word " * 450).strip() + "."
    said = describe_writing_stats(compute_writing_stats(text))
    assert said.startswith("453 words, 3 lines, ")
    assert "2 paragraphs" in said
    assert "2 sentences" in said
    assert "1 long sentence over 30 words" in said
    assert "about 3 minutes to read" in said
    assert "reading grade" in said


def test_the_long_report_for_a_short_text_and_an_empty_one() -> None:
    assert "under a minute to read" in describe_writing_stats(compute_writing_stats("Hi there."))
    empty = describe_writing_stats(compute_writing_stats(""))
    assert "0 words" in empty and "no reading grade" in empty


def test_report_counts_the_selection_when_there_is_one() -> None:
    whole = "one two three four. five six."
    assert statistics_report(whole) == "6 words, 1 line, 29 characters"
    said = statistics_report(whole, "five six.")
    assert said == "Selection: 2 words, 1 line, 9 characters"
    detailed = statistics_report(whole, "five six.", detailed=True)
    assert detailed.startswith("Selection: 2 words") and "1 sentence," in detailed


def test_repeat_press_tells_a_quick_second_press_apart() -> None:
    now = [100.0]
    presses = RepeatPress(clock=lambda: now[0])
    assert presses.press(400) == 1
    now[0] += 0.3
    assert presses.press(400) == 2
    # The press after the long answer starts over.
    now[0] += 0.1
    assert presses.press(400) == 1
    # Too slow to count as a second press.
    now[0] += 1.0
    assert presses.press(400) == 1

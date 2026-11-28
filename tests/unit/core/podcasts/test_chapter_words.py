"""The family's one wording for a chapter: title first, then the time.

Jeff, 2026-11-27: chapters read "Chapter 1, Chapter 2", the position read as a
percentage, and nothing said where he was. Every line here is one a listener
hears, so the tests compare whole sentences.
"""

from __future__ import annotations

from quill.core.podcasts import chapter_words as cw
from quill.core.podcasts.chapters import PodcastChapter

CHAPTERS = [
    PodcastChapter(start_ms=0, title="Welcome"),
    PodcastChapter(start_ms=754_000, title="Listener mail"),
    PodcastChapter(start_ms=1_144_000, title="  "),
]


def test_a_heading_is_title_then_time() -> None:
    assert cw.chapter_heading(CHAPTERS[1]) == "Listener mail, 12:34"


def test_an_untitled_chapter_is_untitled_never_a_number() -> None:
    assert cw.chapter_heading(CHAPTERS[2]) == "Untitled, 19:04"


def test_a_row_says_title_time_length_and_place() -> None:
    row = cw.chapter_row(CHAPTERS, 1, length_ms=3_480_000, playing=True)
    assert row == "Listener mail, 12:34, 6 minutes 30, 2 of 3, playing"


def test_the_last_row_runs_to_the_end_of_the_episode() -> None:
    assert cw.chapter_row(CHAPTERS, 2, length_ms=1_204_000) == "Untitled, 19:04, 1 minute, 3 of 3"


def test_a_row_without_a_known_end_leaves_the_length_out() -> None:
    assert cw.chapter_row(CHAPTERS, 2) == "Untitled, 19:04, 3 of 3"


def test_the_report_line_says_where_the_chapters_came_from() -> None:
    line = cw.chapter_report_line(CHAPTERS, 1, source="Published chapters")
    assert line == "Listener mail, 2 of 3, from the publisher"
    assert cw.chapter_report_line(CHAPTERS, 0, source="") == "Welcome, 1 of 3"


def test_the_position_value_is_a_time_not_a_percentage() -> None:
    assert cw.position_value(754_000, 3_480_000) == "12 minutes 34 of 58 minutes"
    assert cw.position_value(50_000, 0) == "50 seconds"


def test_where_am_i_says_the_chapter_then_the_episode() -> None:
    sentence = cw.where_am_i(1_004_000, 3_480_000, CHAPTERS)
    assert sentence == (
        "Listener mail, 4 minutes 10 into the chapter, 2 minutes 20 left. "
        "16 minutes 44 of 58 minutes, 41 minutes 16 left, 28 percent."
    )


def test_where_am_i_without_chapters_or_length() -> None:
    assert cw.where_am_i(90_000, 0) == "1 minute 30 in."


def test_a_live_stream_says_the_elapsed_time_only() -> None:
    assert cw.where_am_i(720_000, 0, live=True) == "Live, 12 minutes since you tuned in."


def test_the_index_at_a_position() -> None:
    assert cw.chapter_index_at(CHAPTERS, 0) == 0
    assert cw.chapter_index_at(CHAPTERS, 754_000) == 1
    assert cw.chapter_index_at([PodcastChapter(start_ms=5_000, title="x")], 1_000) == -1


def test_span_words() -> None:
    assert cw.span_words(3_600_000) == "1 hour"
    assert cw.span_words(3_660_000) == "1 hour 1 minute"
    assert cw.span_words(1_000) == "1 second"
    assert cw.span_words(120_000) == "2 minutes"

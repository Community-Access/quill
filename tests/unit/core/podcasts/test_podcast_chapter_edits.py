"""Correcting a worked-out chapter list, and what a correction means.

The rule these pin, and the reason the module exists: **a chapter somebody edited
is no longer a guess.** A list that kept describing a mark you moved as "worked
out, 44% sure" would be understating the best information it has, and the report
would be unable to say the one useful thing -- how much of this did I check?
"""

from __future__ import annotations

import pytest

from quill.core.podcasts import chapter_edits
from quill.core.podcasts.chapter_edits import ChapterEditError
from quill.core.podcasts.chapters import PodcastChapter

HOUR_MS = 60 * 60 * 1000


def _inferred(*starts: int) -> list[PodcastChapter]:
    return chapter_edits.normalise(
        [
            PodcastChapter(start_ms=start, title=f"T{start}", source="transcript", confidence=0.44)
            for start in starts
        ],
        HOUR_MS,
    )


# -- an edit is an authorship claim ----------------------------------------------


def test_editing_a_chapter_stops_it_claiming_to_be_a_guess() -> None:
    rows = chapter_edits.retitle(_inferred(0, 600_000), 1, "The interview", total_ms=HOUR_MS)
    assert rows[1].title == "The interview"
    assert rows[1].source == chapter_edits.SOURCE_EDITED
    assert rows[1].confidence == 1.0
    # Untouched rows are untouched: editing one mark says nothing about the rest.
    assert rows[0].source == "transcript"
    assert rows[0].confidence == 0.44


def test_the_summary_says_how_much_was_checked() -> None:
    rows = _inferred(0, 600_000, 1_200_000)
    assert "3 worked out" in chapter_edits.summarise(rows)
    rows = chapter_edits.retitle(rows, 2, "Questions", total_ms=HOUR_MS)
    said = chapter_edits.summarise(rows)
    assert "2 worked out" in said
    assert "1 you corrected" in said


# -- the list stays a partition --------------------------------------------------


def test_the_list_always_opens_at_zero() -> None:
    rows = chapter_edits.normalise([PodcastChapter(start_ms=90_000, title="Late")], HOUR_MS)
    assert rows[0].start_ms == 0, "an episode starts whether or not anybody marked it"


def test_every_chapter_ends_where_the_next_one_starts() -> None:
    rows = _inferred(0, 600_000, 1_200_000)
    assert [c.end_ms for c in rows] == [600_000, 1_200_000, HOUR_MS]
    assert rows[0].duration_ms == 600_000  # so "ten minutes long" is sayable


def test_moving_a_mark_past_its_neighbour_reorders_rather_than_refusing() -> None:
    # Somebody who types 40:00 meant 40:00. Refusing because the row is now
    # third rather than second would be pedantry.
    rows = chapter_edits.retime(_inferred(0, 600_000, 1_200_000), 1, 2_400_000, total_ms=HOUR_MS)
    assert [c.start_ms for c in rows] == [0, 1_200_000, 2_400_000]
    assert rows[2].title == "T600000"


def test_nudging_is_the_cheap_correction() -> None:
    rows = chapter_edits.nudge(_inferred(0, 600_000), 1, -25_000, total_ms=HOUR_MS)
    assert rows[1].start_ms == 575_000
    assert rows[1].source == chapter_edits.SOURCE_EDITED


# -- refusals --------------------------------------------------------------------


def test_the_opening_chapter_cannot_be_deleted() -> None:
    with pytest.raises(ChapterEditError):
        chapter_edits.remove(_inferred(0, 600_000), 0, total_ms=HOUR_MS)


def test_two_marks_cannot_share_a_moment() -> None:
    rows = _inferred(0, 600_000)
    with pytest.raises(ChapterEditError):
        chapter_edits.insert(rows, 600_500, "Duplicate", total_ms=HOUR_MS)
    with pytest.raises(ChapterEditError):
        chapter_edits.retime(rows, 1, 1_000, total_ms=HOUR_MS)


def test_nothing_may_sit_past_the_end_of_the_episode() -> None:
    with pytest.raises(ChapterEditError):
        chapter_edits.insert(_inferred(0, 600_000), HOUR_MS + 1, "Beyond", total_ms=HOUR_MS)


def test_a_chapter_needs_a_title() -> None:
    with pytest.raises(ChapterEditError):
        chapter_edits.retitle(_inferred(0, 600_000), 1, "   ", total_ms=HOUR_MS)


# -- times in and out ------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [("0:00", 0), ("12:34", 754_000), ("1:02:03", 3_723_000), ("90", 90_000)],
)
def test_times_are_read_the_way_people_write_them(text: str, expected: int) -> None:
    assert chapter_edits.parse_clock(text) == expected


@pytest.mark.parametrize("text", ["", "soon", "1:2:3:4", "-5:00"])
def test_a_time_that_is_not_a_time_is_refused(text: str) -> None:
    with pytest.raises(ChapterEditError):
        chapter_edits.parse_clock(text)


def test_the_clock_shows_hours_only_when_there_are_hours() -> None:
    assert chapter_edits.clock(754_000) == "12:34"
    assert chapter_edits.clock(3_723_000) == "1:02:03"


# -- preview ---------------------------------------------------------------------


def test_preview_plays_both_sides_of_the_mark() -> None:
    """The question is *does the programme turn here*, and that needs both sides.

    Playing only forward from the mark tells you what the section is about, which
    is a different question and not the one being asked.
    """
    chapter = PodcastChapter(start_ms=600_000, title="Interview")
    start, end = chapter_edits.preview_window(chapter, total_ms=HOUR_MS, lead_seconds=10)
    assert start == 590_000
    assert end == 610_000


def test_preview_at_the_very_start_does_not_run_backwards() -> None:
    chapter = PodcastChapter(start_ms=0, title="Opening")
    start, end = chapter_edits.preview_window(chapter, total_ms=HOUR_MS, lead_seconds=10)
    assert start == 0
    assert end > start


def test_preview_never_runs_past_the_end() -> None:
    chapter = PodcastChapter(start_ms=HOUR_MS - 2_000, title="Outro")
    _, end = chapter_edits.preview_window(chapter, total_ms=HOUR_MS, lead_seconds=30)
    assert end <= HOUR_MS


# -- what a row says -------------------------------------------------------------


def test_a_row_says_what_it_is_without_a_properties_dialog() -> None:
    """A list mixing published, worked-out and corrected marks has to say which
    is which in the row's own text -- for some listeners that is the only form
    the information ever arrives in."""
    rows = _inferred(0, 600_000)
    said = chapter_edits.row_label(rows[1], 1, len(rows))
    assert "2 of 2" in said
    assert "10:00" in said
    assert "T600000" in said
    assert "44% sure" in said

    corrected = chapter_edits.retitle(rows, 1, "Interview", total_ms=HOUR_MS)
    assert chapter_edits.EDITED_LABEL in chapter_edits.row_label(corrected[1], 1, 2)

    published = PodcastChapter(start_ms=0, title="Intro", end_ms=60_000)
    plain = chapter_edits.row_label(published, 0, 1)
    assert "sure" not in plain, "a published chapter is not hedged"

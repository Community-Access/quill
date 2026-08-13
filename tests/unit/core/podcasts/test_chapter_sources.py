"""Unit tests for the free chapter sources and the cascade over them."""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.chapter_sources import (
    ChapterSet,
    chapter_cascade,
    parse_show_notes_chapters,
)
from quill.core.podcasts.chapters import PodcastChapter

HOUR_MS = 60 * 60 * 1000


def test_plain_timestamp_lines() -> None:
    notes = "00:00 Introduction\n12:30 The interview\n45:10 Listener questions"
    chapters = parse_show_notes_chapters(notes, total_ms=HOUR_MS)
    assert [c.title for c in chapters] == [
        "Introduction",
        "The interview",
        "Listener questions",
    ]
    assert [c.start_ms for c in chapters] == [0, 12 * 60_000 + 30_000, 45 * 60_000 + 10_000]


def test_bulleted_and_dashed_lines() -> None:
    notes = "- 0:00 - Cold open\n* 5:00 - Main story\n- 30:00 - Wrap up"
    assert len(parse_show_notes_chapters(notes, total_ms=HOUR_MS)) == 3


def test_bracketed_and_indexed_lines() -> None:
    notes = "1. [00:00] Welcome\n2. [00:08:20] Deep dive\n3. (00:41:05) Goodbye"
    chapters = parse_show_notes_chapters(notes, total_ms=HOUR_MS)
    assert [c.title for c in chapters] == ["Welcome", "Deep dive", "Goodbye"]


def test_hours_are_understood() -> None:
    notes = "00:00 Start\n1:02:03 Later"
    chapters = parse_show_notes_chapters(notes, total_ms=2 * HOUR_MS)
    assert chapters[1].start_ms == (62 * 60 + 3) * 1000


def test_pipe_separator() -> None:
    notes = "00:00 | Opening\n10:00 | Closing"
    assert [c.title for c in parse_show_notes_chapters(notes, total_ms=HOUR_MS)] == [
        "Opening",
        "Closing",
    ]


def test_a_timestamp_inside_a_sentence_is_not_a_chapter() -> None:
    notes = (
        "In this episode we talk for 45:00 about nothing at all, and it was "
        "recorded at 12:30 in the afternoon."
    )
    assert parse_show_notes_chapters(notes, total_ms=HOUR_MS) == []


def test_a_single_timestamp_is_not_a_chapter_list() -> None:
    assert parse_show_notes_chapters("00:00 Everything", total_ms=HOUR_MS) == []


def test_out_of_order_marks_are_rejected() -> None:
    notes = "10:00 Second\n05:00 First"
    assert parse_show_notes_chapters(notes, total_ms=HOUR_MS) == []


def test_marks_past_the_end_are_rejected() -> None:
    notes = "00:00 Start\n20:00 Middle"
    assert parse_show_notes_chapters(notes, total_ms=10 * 60_000) == []


def test_marks_that_do_not_start_near_the_beginning_are_rejected() -> None:
    notes = "40:00 Late\n50:00 Later"
    assert parse_show_notes_chapters(notes, total_ms=2 * HOUR_MS) == []


def test_marks_crammed_together_are_rejected() -> None:
    notes = "00:00 One\n00:05 Two\n00:10 Three"
    assert parse_show_notes_chapters(notes, total_ms=HOUR_MS) == []


def test_titles_are_required() -> None:
    notes = "00:00\n10:00"
    assert parse_show_notes_chapters(notes, total_ms=HOUR_MS) == []


def test_empty_notes() -> None:
    assert parse_show_notes_chapters("", total_ms=HOUR_MS) == []


# -- the cascade ---------------------------------------------------------------


def _published(*titles: str) -> list[PodcastChapter]:
    return [PodcastChapter(start_ms=i * 10 * 60_000, title=title) for i, title in enumerate(titles)]


def test_published_chapters_win() -> None:
    result = chapter_cascade(
        published=lambda: _published("One", "Two"),
        show_notes="00:00 Ignored\n10:00 Also ignored",
        total_ms=HOUR_MS,
    )
    assert result.source == "published"
    assert result.label == "Published chapters"
    assert result.authored is True
    assert [c.title for c in result.chapters] == ["One", "Two"]


def test_show_notes_are_used_when_the_feed_has_none() -> None:
    result = chapter_cascade(
        published=list,
        show_notes="00:00 Opening\n15:00 Closing",
        total_ms=HOUR_MS,
    )
    assert result.source == "show_notes"
    assert result.label == "From the show notes"


def test_a_failing_published_source_falls_through_rather_than_raising() -> None:
    def explode() -> list[PodcastChapter]:
        raise RuntimeError("network is down")

    result = chapter_cascade(published=explode, show_notes="00:00 A\n15:00 B", total_ms=HOUR_MS)
    assert result.source == "show_notes"


def test_nothing_free_found_is_an_empty_set_not_an_error() -> None:
    result = chapter_cascade(published=list, show_notes="no timestamps here", total_ms=HOUR_MS)
    assert result.source == ""
    assert result.label == ""
    assert bool(result) is False


def test_short_episodes_are_skipped_entirely() -> None:
    result = chapter_cascade(
        published=lambda: _published("One", "Two"),
        total_ms=5 * 60_000,
    )
    assert bool(result) is False


def test_chapters_are_sorted_deduplicated_and_clamped() -> None:
    messy = [
        PodcastChapter(start_ms=20 * 60_000, title="Later"),
        PodcastChapter(start_ms=0, title="First"),
        PodcastChapter(start_ms=0, title="Duplicate start"),
        PodcastChapter(start_ms=5 * HOUR_MS, title="Past the end"),
    ]
    result = chapter_cascade(published=lambda: messy, total_ms=HOUR_MS)
    assert [c.title for c in result.chapters] == ["First", "Later"]


def test_a_missing_audio_file_is_simply_skipped(tmp_path: Path) -> None:
    result = chapter_cascade(
        published=list,
        audio_path=tmp_path / "not-there.mp3",
        show_notes="00:00 A\n15:00 B",
        total_ms=HOUR_MS,
    )
    assert result.source == "show_notes"


def test_empty_chapter_set_is_falsy_and_unlabelled() -> None:
    assert bool(ChapterSet()) is False
    assert ChapterSet().label == ""

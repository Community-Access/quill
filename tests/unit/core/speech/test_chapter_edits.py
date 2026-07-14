"""Tests for chapter surgery: merge, split-at-playhead, retime, clamp."""

from __future__ import annotations

import pytest

from quill.core.speech.chapters import (
    Chapter,
    ChapterEditError,
    clamp_chapters,
    merge_chapter,
    set_chapter_start,
    split_chapter,
)


def _chapters() -> list[Chapter]:
    return [
        Chapter(index=0, title="One", start_ms=0, end_ms=60_000),
        Chapter(index=1, title="Two", start_ms=60_000, end_ms=120_000),
        Chapter(index=2, title="Three", start_ms=120_000, end_ms=200_000),
    ]


def _total(chapters: list[Chapter]) -> int:
    return chapters[-1].end_ms - chapters[0].start_ms


def test_merge_middle_into_previous() -> None:
    merged = merge_chapter(_chapters(), 1)
    assert [c.title for c in merged] == ["One", "Three"]
    assert merged[0].end_ms == 120_000
    assert _total(merged) == 200_000
    assert [c.index for c in merged] == [0, 1]


def test_merge_first_keeps_first_title() -> None:
    merged = merge_chapter(_chapters(), 0)
    assert [c.title for c in merged] == ["One", "Three"]
    assert merged[0].end_ms == 120_000


def test_merge_requires_two_and_valid_index() -> None:
    with pytest.raises(ChapterEditError):
        merge_chapter(_chapters()[:1], 0)
    with pytest.raises(ChapterEditError):
        merge_chapter(_chapters(), 7)


def test_split_at_playhead_preserves_total_duration() -> None:
    result = split_chapter(_chapters(), 90_000, title="New chapter")
    assert [c.title for c in result] == ["One", "Two", "New chapter", "Three"]
    assert result[1].end_ms == 90_000 and result[2].start_ms == 90_000
    assert _total(result) == 200_000
    assert [c.index for c in result] == [0, 1, 2, 3]


def test_split_too_close_to_boundary_raises() -> None:
    with pytest.raises(ChapterEditError):
        split_chapter(_chapters(), 60_500)  # 500 ms into Two, min part is 1000
    with pytest.raises(ChapterEditError):
        split_chapter(_chapters(), 250_000)  # outside every chapter


def test_set_chapter_start_moves_boundary() -> None:
    result = set_chapter_start(_chapters(), 1, 45_000)
    assert result[0].end_ms == 45_000
    assert result[1].start_ms == 45_000
    assert _total(result) == 200_000


def test_set_chapter_start_bounds() -> None:
    with pytest.raises(ChapterEditError):
        set_chapter_start(_chapters(), 0, 10)  # first chapter is pinned
    with pytest.raises(ChapterEditError):
        set_chapter_start(_chapters(), 1, 200)  # leaves previous too short
    with pytest.raises(ChapterEditError):
        set_chapter_start(_chapters(), 1, 119_900)  # leaves this one too short


def test_clamp_chapters_shrinks_and_drops() -> None:
    clamped = clamp_chapters(_chapters(), 100_000)
    assert [c.title for c in clamped] == ["One", "Two"]
    assert clamped[-1].end_ms == 100_000
    assert clamp_chapters(_chapters(), 0) == []


def test_clamp_extends_final_chapter_to_total() -> None:
    clamped = clamp_chapters(_chapters(), 250_000)
    assert clamped[-1].end_ms == 250_000

"""Tests for chapter-list import/export (Audacity, CUE, timestamps, pod2, CSV)."""

from __future__ import annotations

import json

import pytest

from quill.core.speech.chapter_io import (
    ChapterParseError,
    chapters_to_audacity,
    chapters_to_csv,
    chapters_to_cue,
    chapters_to_pod2,
    chapters_to_timestamps,
    export_chapter_text,
    format_timestamp,
    parse_chapter_text,
    suggested_extension,
)
from quill.core.speech.chapters import Chapter


def _chapters() -> list[Chapter]:
    return [
        Chapter(index=0, title="Intro", start_ms=0, end_ms=60_000),
        Chapter(index=1, title="The Long Road", start_ms=60_000, end_ms=3_723_000),
        Chapter(index=2, title="Coda", start_ms=3_723_000, end_ms=3_900_000),
    ]


def test_format_timestamp() -> None:
    assert format_timestamp(0) == "0:00"
    assert format_timestamp(61_000) == "1:01"
    assert format_timestamp(3_723_000) == "1:02:03"


def test_audacity_round_trip() -> None:
    text = chapters_to_audacity(_chapters())
    assert "0.000000\t60.000000\tIntro" in text
    parsed = parse_chapter_text(text, 3_900_000)
    assert [c.title for c in parsed] == ["Intro", "The Long Road", "Coda"]
    assert [c.start_ms for c in parsed] == [0, 60_000, 3_723_000]
    assert parsed[-1].end_ms == 3_900_000


def test_timestamps_round_trip() -> None:
    text = chapters_to_timestamps(_chapters())
    assert text.splitlines()[1] == "1:00\tThe Long Road"
    parsed = parse_chapter_text(text, 3_900_000)
    assert [c.title for c in parsed] == ["Intro", "The Long Road", "Coda"]


def test_cue_round_trip_with_tags() -> None:
    text = chapters_to_cue(_chapters(), "book.mp3", performer="Jane Doe", album="My Book")
    assert 'PERFORMER "Jane Doe"' in text
    assert 'FILE "book.mp3" MP3' in text
    assert "INDEX 01 00:00:00" in text
    parsed = parse_chapter_text(text, 3_900_000)
    assert [c.title for c in parsed] == ["Intro", "The Long Road", "Coda"]
    # CUE index frames are 1/75 s, so starts survive to the frame.
    assert parsed[1].start_ms == 60_000


def test_pod2_round_trip() -> None:
    text = chapters_to_pod2(_chapters())
    data = json.loads(text)
    assert data["version"] == "1.2.0"
    assert data["chapters"][1] == {"startTime": 60.0, "title": "The Long Road"}
    parsed = parse_chapter_text(text, 3_900_000)
    assert [c.start_ms for c in parsed] == [0, 60_000, 3_723_000]


def test_pod2_url_and_image_round_trip() -> None:
    chapters = _chapters()
    chapters[1].url = "https://example.com/road"
    chapters[1].image = "https://example.com/road.jpg"
    text = chapters_to_pod2(chapters)
    data = json.loads(text)
    assert data["chapters"][1]["url"] == "https://example.com/road"
    assert data["chapters"][1]["img"] == "https://example.com/road.jpg"
    assert "url" not in data["chapters"][0]  # empty extras are omitted
    parsed = parse_chapter_text(text, 3_900_000)
    assert parsed[1].url == "https://example.com/road"
    assert parsed[1].image == "https://example.com/road.jpg"
    assert parsed[0].url == "" and parsed[0].image == ""


def test_csv_export_shape() -> None:
    text = chapters_to_csv(_chapters())
    lines = text.splitlines()
    assert lines[0] == "#,Title,Start,Duration"
    assert lines[1] == "1,Intro,0:00,1:00"


def test_export_chapter_text_dispatch_and_extensions() -> None:
    for fmt in ("audacity", "timestamps", "cue", "pod2", "csv"):
        assert export_chapter_text(_chapters(), fmt, audio_filename="b.mp3")
    with pytest.raises(ValueError):
        export_chapter_text(_chapters(), "nope")
    assert suggested_extension("pod2") == ".chapters.json"
    assert suggested_extension("cue") == ".cue"


def test_parse_inserts_missing_zero_marker() -> None:
    parsed = parse_chapter_text("2:00\tLate start\n", 300_000)
    assert parsed[0].start_ms == 0 and parsed[0].title == "Chapter 1"
    assert parsed[1].start_ms == 120_000 and parsed[1].title == "Late start"
    assert parsed[-1].end_ms == 300_000


def test_parse_drops_markers_beyond_duration_and_junk() -> None:
    text = "# comment\n0:00 Intro\n5:00 Too far\nnot a marker\n1:00 - Middle\n"
    parsed = parse_chapter_text(text, 180_000)
    assert [c.title for c in parsed] == ["Intro", "Middle"]
    assert parsed[1].start_ms == 60_000  # the "- " prefix is stripped


def test_parse_nothing_usable_raises() -> None:
    with pytest.raises(ChapterParseError):
        parse_chapter_text("no chapters here\n", 60_000)
    with pytest.raises(ChapterParseError):
        parse_chapter_text("0:30 Something\n", 0)


def test_titles_from_text_plain_lines_and_timestamps() -> None:
    from quill.core.speech.chapter_io import titles_from_text

    assert titles_from_text("Intro\nBody\n# note\n\nCoda\n") == ["Intro", "Body", "Coda"]
    assert titles_from_text("0:00 Intro\n1:00 - Body\n") == ["Intro", "Body"]
    assert titles_from_text(chapters_to_audacity(_chapters())) == [
        "Intro",
        "The Long Road",
        "Coda",
    ]
    assert titles_from_text(chapters_to_pod2(_chapters()))[0] == "Intro"
    assert titles_from_text(chapters_to_cue(_chapters(), "b.mp3"))[2] == "Coda"


def test_titles_from_text_csv_with_title_header() -> None:
    from quill.core.speech.chapter_io import titles_from_text

    # Our own CSV export round-trips.
    assert titles_from_text(chapters_to_csv(_chapters())) == [
        "Intro",
        "The Long Road",
        "Coda",
    ]
    # A hand-made sheet with a Title column, any position, any extra columns.
    text = "File,Title,Notes\n01.mp3,Intro,\n02.mp3,Body,keep\n"
    assert titles_from_text(text) == ["Intro", "Body"]
    # Headerless numeric-first-column CSV: the second column is the title.
    assert titles_from_text("1,One\n2,Two\n") == ["One", "Two"]
    # An empty title cell falls back to a generated name.
    assert titles_from_text("#,Title\n1,\n2,Real\n") == ["Chapter 1", "Real"]


def test_parse_duplicate_starts_keep_first_title() -> None:
    parsed = parse_chapter_text("0:00\tFirst\n0:00\tSecond\n1:00\tNext\n", 120_000)
    assert parsed[0].title == "First"
    assert len(parsed) == 2

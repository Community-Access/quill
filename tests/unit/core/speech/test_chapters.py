"""Unit tests for MP3 chapter markers (batch-document-to-speech §4.8.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech.chapters import (
    Chapter,
    ChapterSection,
    compute_chapters,
    read_mp3_chapters,
    write_mp3_chapters,
)

mutagen = pytest.importorskip("mutagen")


# -- compute_chapters ------------------------------------------------------ #


def _sections(*pairs: tuple[str, int]) -> list[ChapterSection]:
    return [ChapterSection(title=t, duration_ms=d) for t, d in pairs]


def test_compute_chapters_no_gap_is_cumulative() -> None:
    chapters = compute_chapters(_sections(("Intro", 1000), ("One", 2000), ("Two", 1500)))
    assert [(c.start_ms, c.end_ms) for c in chapters] == [
        (0, 1000),
        (1000, 3000),
        (3000, 4500),
    ]
    assert [c.title for c in chapters] == ["Intro", "One", "Two"]
    assert [c.index for c in chapters] == [0, 1, 2]


def test_compute_chapters_with_gap_is_contiguous() -> None:
    # The gap is the trailing part of the preceding chapter — never after the
    # last — so chapters tile the timeline with no holes (the ChapterForge fix).
    chapters = compute_chapters(
        _sections(("Intro", 1000), ("One", 2000), ("Two", 1500)), gap_ms=500
    )
    assert [(c.start_ms, c.end_ms) for c in chapters] == [
        (0, 1500),  # 1000 audio + 500 trailing gap
        (1500, 4000),  # 2000 audio + 500 trailing gap
        (4000, 5500),  # 1500 audio, no trailing gap (last)
    ]
    # contiguity: every chapter starts exactly where the previous ended
    for prev, nxt in zip(chapters, chapters[1:], strict=False):
        assert prev.end_ms == nxt.start_ms


def test_compute_chapters_single_section_has_no_trailing_gap() -> None:
    chapters = compute_chapters(_sections(("Only", 3000)), gap_ms=1000)
    assert [(c.start_ms, c.end_ms) for c in chapters] == [(0, 3000)]


def test_compute_chapters_empty() -> None:
    assert compute_chapters([]) == []


def test_compute_chapters_negative_values_are_floored() -> None:
    chapters = compute_chapters(_sections(("A", -50), ("B", 100)), gap_ms=-10)
    # negative duration floored to 0, negative gap floored to 0
    assert [(c.start_ms, c.end_ms) for c in chapters] == [(0, 0), (0, 100)]


def test_chapter_duration_ms() -> None:
    assert Chapter(index=0, title="x", start_ms=100, end_ms=450).duration_ms == 350


# -- MP3 write / read round-trip ------------------------------------------- #


@pytest.fixture
def silent_mp3(tmp_path: Path) -> Path:
    """A minimal valid MP3 (a single silent frame) to tag in place."""
    # One MPEG-1 Layer III frame header + padding is enough for mutagen to
    # treat the file as an MP3 and attach an ID3 tag. We write a tiny silent
    # frame so save()/load() round-trips without needing a real encoder.
    path = tmp_path / "audio.mp3"
    # 0xFF 0xFB = MPEG1 L3, 128kbps, 44.1kHz, no CRC; pad with zeroes.
    frame = b"\xff\xfb\x90\x00" + b"\x00" * 413
    path.write_bytes(frame * 4)
    return path


def test_write_and_read_round_trip(silent_mp3: Path) -> None:
    chapters = compute_chapters(
        _sections(("Intro", 1000), ("Story One", 2000), ("Story Two", 1500)), gap_ms=500
    )
    write_mp3_chapters(silent_mp3, chapters)
    out = read_mp3_chapters(silent_mp3)
    assert [c.title for c in out] == ["Intro", "Story One", "Story Two"]
    assert [(c.start_ms, c.end_ms) for c in out] == [(0, 1500), (1500, 4000), (4000, 5500)]


def test_write_is_idempotent(silent_mp3: Path) -> None:
    chapters = compute_chapters(_sections(("One", 1000), ("Two", 1000)))
    write_mp3_chapters(silent_mp3, chapters)
    write_mp3_chapters(silent_mp3, chapters)  # second pass must not duplicate
    out = read_mp3_chapters(silent_mp3)
    assert [c.title for c in out] == ["One", "Two"]


def test_write_preserves_existing_tags(silent_mp3: Path) -> None:
    # Pre-seed an unrelated frame; the chapter writer must not clobber it
    # (the ChapterForge fix: load existing tags instead of fresh ID3()).
    from mutagen.id3 import ID3, TIT2

    tags = ID3()
    tags.add(TIT2(encoding=3, text=["My Album Title"]))
    tags.save(str(silent_mp3))

    write_mp3_chapters(silent_mp3, compute_chapters(_sections(("One", 1000))))

    reloaded = ID3(str(silent_mp3))
    title = reloaded.getall("TIT2")
    assert title and str(title[0].text[0]) == "My Album Title"
    assert len(reloaded.getall("CHAP")) == 1


def test_write_no_chapters_writes_no_ctoc(silent_mp3: Path) -> None:
    write_mp3_chapters(silent_mp3, [])
    from mutagen.id3 import ID3, ID3NoHeaderError

    try:
        tags = ID3(str(silent_mp3))
    except ID3NoHeaderError:
        return  # nothing written at all is also acceptable
    assert tags.getall("CHAP") == []
    assert tags.getall("CTOC") == []


def test_custom_toc_title(silent_mp3: Path) -> None:
    write_mp3_chapters(silent_mp3, compute_chapters(_sections(("One", 1000))), toc_title="Articles")
    from mutagen.id3 import ID3

    tags = ID3(str(silent_mp3))
    ctoc = tags.getall("CTOC")
    assert ctoc
    sub = ctoc[0].sub_frames.get("TIT2")
    assert sub is not None and str(sub.text[0]) == "Articles"

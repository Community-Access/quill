"""Tests for silence detection parsing and auto-chapter proposals (pure parts)."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.silence import (
    build_silence_detect_command,
    build_silence_trim_command,
    parse_silence_log,
    propose_chapters_from_silences,
)

_LOG = """
[silencedetect @ 0x1] silence_start: 10.5
[silencedetect @ 0x1] silence_end: 11.5 | silence_duration: 1.0
[silencedetect @ 0x1] silence_start: 30.0
[silencedetect @ 0x1] silence_end: 31.0 | silence_duration: 1.0
"""


def test_parse_silence_log_pairs_starts_with_ends() -> None:
    assert parse_silence_log(_LOG) == [(10.5, 11.5), (30.0, 31.0)]


def test_parse_silence_log_trailing_start_pairs_with_itself() -> None:
    text = "silence_start: 55.0\n"
    assert parse_silence_log(text) == [(55.0, 55.0)]


def test_propose_chapters_tiles_whole_file() -> None:
    chapters = propose_chapters_from_silences([(10.5, 11.5), (30.0, 31.0)], 60_000)
    assert [c.start_ms for c in chapters] == [0, 11_000, 30_500]
    assert chapters[-1].end_ms == 60_000
    assert [c.title for c in chapters] == ["Chapter 1", "Chapter 2", "Chapter 3"]
    # Contiguous: each end meets the next start.
    for a, b in zip(chapters, chapters[1:], strict=False):
        assert a.end_ms == b.start_ms


def test_propose_chapters_merges_short_slivers() -> None:
    # A silence 1 s in would make a 1-second first chapter; it merges away.
    chapters = propose_chapters_from_silences([(1.0, 1.2)], 60_000, min_chapter_ms=5000)
    assert len(chapters) == 1
    assert chapters[0].start_ms == 0 and chapters[0].end_ms == 60_000


def test_propose_chapters_no_silences_is_one_chapter() -> None:
    chapters = propose_chapters_from_silences([], 45_000)
    assert len(chapters) == 1
    assert chapters[0].duration_ms == 45_000


def test_detect_command_shape() -> None:
    args = build_silence_detect_command("ffmpeg", Path("in.mp3"), noise_db=-30.0, min_silence_s=0.8)
    assert args[0] == "ffmpeg"
    assert "silencedetect=noise=-30.0dB:d=0.8" in args
    assert args[-2:] == ["null", "-"]


def test_trim_command_uses_reverse_trick() -> None:
    args = build_silence_trim_command("ffmpeg", Path("in.mp3"), Path("out.mp3"))
    af = args[args.index("-af") + 1]
    assert af.count("areverse") == 2
    assert af.count("silenceremove") == 2
    assert args[-1] == "out.mp3"

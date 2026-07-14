"""Tests for the audio surgery argv builders and helpers (pure parts)."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.audio_edit import (
    atempo_filter,
    build_fade_command,
    build_tempo_command,
    build_trim_command,
    safe_chapter_filename,
)


def test_trim_command_bounds() -> None:
    args = build_trim_command(
        "ffmpeg", Path("in.mp3"), Path("out.mp3"), start_ms=1500, end_ms=61_500
    )
    assert args[args.index("-ss") + 1] == "1.500"
    assert args[args.index("-to") + 1] == "61.500"
    assert args[-1] == "out.mp3"


def test_atempo_filter_single_stage() -> None:
    assert atempo_filter(1.25) == "atempo=1.25"
    assert atempo_filter(0.75) == "atempo=0.75"


def test_atempo_filter_chains_beyond_range() -> None:
    assert atempo_filter(3.0) == "atempo=2.0,atempo=1.5"
    assert atempo_filter(0.4) == "atempo=0.5,atempo=0.8"
    # Clamped to sane bounds rather than exploding (4.0 = two doublings).
    assert atempo_filter(100.0) == "atempo=2.0,atempo=2"


def test_tempo_command_uses_filter() -> None:
    args = build_tempo_command("ffmpeg", Path("a.mp3"), Path("b.mp3"), speed=1.5)
    assert args[args.index("-af") + 1] == "atempo=1.5"


def test_fade_command_places_fade_out_at_tail() -> None:
    args = build_fade_command(
        "ffmpeg",
        Path("a.mp3"),
        Path("b.mp3"),
        duration_ms=60_000,
        fade_in_ms=500,
        fade_out_ms=2_000,
    )
    af = args[args.index("-af") + 1]
    assert "afade=t=in:st=0:d=0.500" in af
    assert "afade=t=out:st=58.000:d=2.000" in af


def test_fade_command_no_fades_is_null_filter() -> None:
    args = build_fade_command("ffmpeg", Path("a.mp3"), Path("b.mp3"), duration_ms=60_000)
    assert args[args.index("-af") + 1] == "anull"


def test_safe_chapter_filename_strips_unsafe_characters() -> None:
    assert safe_chapter_filename(3, 'The "End"? Yes: really/truly', ".mp3") == (
        "03 - The End Yes reallytruly.mp3"
    )
    assert safe_chapter_filename(1, "  ", ".m4a") == "01 - Chapter 1.m4a"

"""Tests for AI chapter-title proposals (pure parts; no ffmpeg, no network)."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.chapter_titles import (
    build_opening_slice_command,
    clean_title,
    propose_chapter_titles,
)
from quill.core.speech.chapters import Chapter


def _chapters() -> list[Chapter]:
    return [
        Chapter(index=0, title="track01", start_ms=0, end_ms=120_000),
        Chapter(index=1, title="track02", start_ms=120_000, end_ms=150_000),
    ]


def test_slice_command_shape(tmp_path: Path) -> None:
    args = build_opening_slice_command(
        "ffmpeg", tmp_path / "book.m4b", 120_000, 30_000, tmp_path / "o.wav"
    )
    assert args[0] == "ffmpeg" and args[-1] == str(tmp_path / "o.wav")
    assert args[args.index("-ss") + 1] == "120.000"
    assert args[args.index("-t") + 1] == "30.000"
    assert args[args.index("-ar") + 1] == "16000"  # whisper-friendly shape
    assert args[args.index("-ac") + 1] == "1"


def test_clean_title_strips_wrapping_and_clamps() -> None:
    assert clean_title('"The Long Road Home."', "x") == "The Long Road Home"
    assert clean_title("Title: A Quiet Start\nExtra line", "x") == "A Quiet Start"
    assert clean_title("", "keep me") == "keep me"
    assert clean_title("one two three four five six seven eight nine ten", "x") == (
        "one two three four five six seven eight"
    )


def test_propose_titles_uses_transcript_and_keeps_old_on_failure(
    tmp_path: Path, monkeypatch
) -> None:
    import quill.core.speech.chapter_titles as ct

    monkeypatch.setattr(ct, "slice_chapter_opening", lambda book, ch, out, seconds=60: out)
    transcripts = {0: "we begin the journey at dawn", 1: ""}
    calls: list[str] = []

    def transcribe(wav: Path) -> str:
        return transcripts[int(wav.stem.split("_")[1])]

    def ask(prompt: str) -> str:
        calls.append(prompt)
        assert "we begin the journey" in prompt
        return "Dawn Departure"

    titles = propose_chapter_titles(
        tmp_path / "book.m4b", _chapters(), ask, tmp_path, transcribe=transcribe
    )
    # Chapter 1 gets the AI title; chapter 2 had no transcript so keeps its own.
    assert titles == ["Dawn Departure", "track02"]
    assert len(calls) == 1


def test_propose_titles_cancel_keeps_remaining_titles(tmp_path: Path, monkeypatch) -> None:
    import quill.core.speech.chapter_titles as ct

    monkeypatch.setattr(ct, "slice_chapter_opening", lambda book, ch, out, seconds=60: out)
    titles = propose_chapter_titles(
        tmp_path / "book.m4b",
        _chapters(),
        lambda prompt: "New",
        tmp_path,
        transcribe=lambda wav: "text",
        is_cancelled=lambda: True,
    )
    assert titles == ["track01", "track02"]

"""Tests for native M4B chapter atoms via ffmpeg FFMETADATA (§1.2 / ChapterForge)."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.ffmpeg import (
    AudioMetadata,
    build_ffmetadata,
    build_m4b_command,
)


def test_ffmetadata_has_header_and_chapter_blocks() -> None:
    meta = AudioMetadata(album="My Book", artist="Jeff", genre="Audiobook", year="2026")
    doc = build_ffmetadata([("Chapter One", 0, 60000), ("Chapter Two", 60000, 125000)], meta)
    assert doc.startswith(";FFMETADATA1\n")
    assert "album=My Book" in doc
    assert "artist=Jeff" in doc
    # Two chapters with millisecond timebase and titles.
    assert doc.count("[CHAPTER]") == 2
    assert "TIMEBASE=1/1000" in doc
    assert "START=0" in doc and "END=60000" in doc
    assert "START=60000" in doc and "END=125000" in doc
    assert "title=Chapter One" in doc and "title=Chapter Two" in doc


def test_ffmetadata_escapes_special_characters() -> None:
    doc = build_ffmetadata([("A = B; C # D", 0, 1000)])
    # The reserved FFMETADATA characters are backslash-escaped in the title line.
    assert r"title=A \= B\; C \# D" in doc


def test_ffmetadata_without_metadata_is_chapters_only() -> None:
    doc = build_ffmetadata([("Only", 0, 500)])
    assert doc.startswith(";FFMETADATA1\n")
    assert "album=" not in doc
    assert "[CHAPTER]" in doc


def test_m4b_command_maps_chapters_and_uses_ipod_muxer() -> None:
    cmd = build_m4b_command("ffmpeg", Path("in.wav"), Path("meta.ffmeta"), Path("out.m4b"))
    # The metadata file is the second input, mapped for tags and chapters.
    assert cmd.count("-i") == 2
    assert cmd[cmd.index("-map_chapters") + 1] == "1"
    assert cmd[cmd.index("-map_metadata") + 1] == "1"
    assert cmd[cmd.index("-f") + 1] == "ipod"  # Apple M4B container
    assert cmd[cmd.index("-c:a") + 1] == "aac"
    assert cmd[-1] == "out.m4b"

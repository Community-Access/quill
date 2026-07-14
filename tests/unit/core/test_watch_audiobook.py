"""Tests for the build-audiobook watch action (validation/preview/coalescing)."""

from __future__ import annotations

from pathlib import Path

from quill.core.watch_actions import WatchItem, default_registry
from quill.core.watch_audiobook import BuildAudiobookAction, master_path


def _item(path: Path) -> WatchItem:
    return WatchItem(source_path=path)


def test_registered_in_default_registry() -> None:
    registry = default_registry()
    assert registry.get("build_audiobook") is not None


def test_validate_format() -> None:
    action = BuildAudiobookAction()
    assert action.validate({"format": "m4b"}) == []
    assert action.validate({}) == []  # defaults to m4b
    assert action.validate({"format": "ogg"})


def test_preview_names_master(tmp_path: Path) -> None:
    action = BuildAudiobookAction()
    audio = tmp_path / "Book" / "01.mp3"
    audio.parent.mkdir()
    audio.write_bytes(b"x")
    text = action.preview(_item(audio), {"format": "mp3"})
    assert "Book - Master.mp3" in text and "Book" in text


def test_run_skips_non_audio_and_current_master(tmp_path: Path) -> None:
    action = BuildAudiobookAction()
    folder = tmp_path / "Book"
    folder.mkdir()
    doc = folder / "notes.txt"
    doc.write_text("x", encoding="utf-8")
    outcome = action.run(_item(doc), {})
    assert outcome.status == "skipped"

    audio = folder / "01.mp3"
    audio.write_bytes(b"x")
    master = master_path(folder, "m4b")
    master.write_bytes(b"m")  # master newer than the audio -> coalesced skip
    outcome = action.run(_item(audio), {})
    assert outcome.status == "skipped"
    assert "already current" in outcome.message

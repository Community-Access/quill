"""Tests for the Audio Studio per-book prefs store (Phase 2 port-in)."""

from __future__ import annotations

from pathlib import Path

from quill.core.audio_studio.book_prefs import (
    BookPrefsStore,
    get_prefs,
    load_prefs,
    save_prefs,
    set_muted,
    set_volume,
)


def test_default_unset() -> None:
    s = BookPrefsStore()
    assert get_prefs(s, "x").volume_percent == -1
    assert get_prefs(s, "x").muted is False


def test_set_volume_clamps_and_persists(tmp_path: Path) -> None:
    s = BookPrefsStore()
    assert set_volume(s, "x", 150) is True
    assert get_prefs(s, "x").volume_percent == 100
    assert set_volume(s, "x", -20) is True
    assert get_prefs(s, "x").volume_percent == 0
    set_volume(s, "x", 42)
    save_prefs(tmp_path, s)
    assert load_prefs(tmp_path).entries["x"].volume_percent == 42


def test_set_volume_unchanged_returns_false() -> None:
    s = BookPrefsStore()
    set_volume(s, "x", 50)
    assert set_volume(s, "x", 50) is False


def test_mute_round_trip(tmp_path: Path) -> None:
    s = BookPrefsStore()
    set_muted(s, "x", True)
    save_prefs(tmp_path, s)
    got = load_prefs(tmp_path)
    assert got.entries["x"].muted is True
    set_muted(s, "x", False)
    save_prefs(tmp_path, s)
    assert load_prefs(tmp_path).entries["x"].muted is False


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    got = load_prefs(tmp_path)
    assert got.entries == {}


def test_load_broken_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "audio_studio_book_prefs.json").write_text("{bad", encoding="utf-8")
    assert load_prefs(tmp_path).entries == {}


def test_get_prefs_does_not_create_entry() -> None:
    s = BookPrefsStore()
    get_prefs(s, "x")
    assert "x" not in s.entries

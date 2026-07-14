"""Unit tests for the voice-failure blacklist (batch robustness, roadmap §5)."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.voice_blacklist import (
    VoiceBlacklist,
    load_blacklist,
    save_blacklist,
    voice_key,
)


def test_voice_key_is_case_insensitive() -> None:
    assert voice_key("SAPI5", "David") == voice_key("sapi5", "david")


def test_record_and_is_blacklisted() -> None:
    bl = VoiceBlacklist()
    assert bl.is_blacklisted("sapi5", "david") is False
    bl.record_failure("sapi5", "David", "engine crashed")
    assert bl.is_blacklisted("sapi5", "david") is True  # case-insensitive match
    entry = bl.entries[voice_key("sapi5", "david")]
    assert entry.count == 1 and entry.last_error == "engine crashed"


def test_threshold_requires_repeated_failures() -> None:
    bl = VoiceBlacklist()
    bl.record_failure("espeak", "es")
    assert bl.is_blacklisted("espeak", "es", threshold=2) is False
    bl.record_failure("espeak", "es")
    assert bl.is_blacklisted("espeak", "es", threshold=2) is True


def test_filter_voices_drops_blacklisted_preserving_order() -> None:
    bl = VoiceBlacklist()
    bl.record_failure("sapi5", "bad")
    assert bl.filter_voices("sapi5", ["a", "bad", "b"]) == ["a", "b"]


def test_clear_scopes() -> None:
    bl = VoiceBlacklist()
    bl.record_failure("sapi5", "a")
    bl.record_failure("sapi5", "b")
    bl.record_failure("espeak", "es")
    bl.clear("sapi5", "a")  # one entry
    assert not bl.is_blacklisted("sapi5", "a") and bl.is_blacklisted("sapi5", "b")
    bl.clear("sapi5")  # all of one engine
    assert not bl.is_blacklisted("sapi5", "b") and bl.is_blacklisted("espeak", "es")
    bl.clear()  # everything
    assert not bl.entries


def test_round_trip_to_disk(tmp_path: Path) -> None:
    bl = VoiceBlacklist()
    bl.record_failure("kokoro", "af_heart", "missing model")
    path = tmp_path / "voice-blacklist.json"
    save_blacklist(bl, path)
    loaded = load_blacklist(path)
    assert loaded.is_blacklisted("kokoro", "af_heart")
    assert loaded.entries[voice_key("kokoro", "af_heart")].last_error == "missing model"


def test_load_missing_or_corrupt_is_empty(tmp_path: Path) -> None:
    assert load_blacklist(tmp_path / "absent.json").entries == {}
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    assert load_blacklist(corrupt).entries == {}

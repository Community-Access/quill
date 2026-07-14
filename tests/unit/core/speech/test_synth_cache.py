"""Tests for the incremental-rebuild fingerprint cache."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.synth_cache import (
    can_reuse,
    fingerprint,
    load_cache,
    save_cache,
    settings_digest,
)

_SETTINGS: dict[str, object] = {"engine": "kokoro", "voice": "af_bella", "gaps": [900, 0, 0]}


def test_fingerprint_changes_with_content_and_settings(tmp_path: Path) -> None:
    doc = tmp_path / "ch1.md"
    doc.write_text("# One\nHello.", encoding="utf-8")
    base = fingerprint(doc, _SETTINGS)
    assert base == fingerprint(doc, dict(_SETTINGS))  # stable across calls/dict copies

    doc.write_text("# One\nHello again.", encoding="utf-8")
    assert fingerprint(doc, _SETTINGS) != base

    doc.write_text("# One\nHello.", encoding="utf-8")
    assert fingerprint(doc, _SETTINGS) == base  # content restored, key restored
    assert fingerprint(doc, {**_SETTINGS, "voice": "af_heart"}) != base


def test_settings_digest_is_order_insensitive() -> None:
    assert settings_digest({"a": 1, "b": [2, 3]}) == settings_digest({"b": [2, 3], "a": 1})


def test_cache_round_trip_and_junk_tolerance(tmp_path: Path) -> None:
    save_cache(tmp_path, {"ch1.md": "abc", "sub/ch2.md": "def"})
    assert load_cache(tmp_path) == {"ch1.md": "abc", "sub/ch2.md": "def"}
    (tmp_path / ".quill" / "speech-cache.json").write_text("not json", encoding="utf-8")
    assert load_cache(tmp_path) == {}
    assert load_cache(tmp_path / "nowhere") == {}


def test_can_reuse_requires_output_record_and_match(tmp_path: Path) -> None:
    doc = tmp_path / "ch1.md"
    doc.write_text("# One\nHello.", encoding="utf-8")
    out = tmp_path / "ch1.mp3"
    entries = {"ch1.md": fingerprint(doc, _SETTINGS)}

    assert not can_reuse(entries, "ch1.md", doc, out, _SETTINGS)  # no output yet
    out.write_bytes(b"audio")
    assert can_reuse(entries, "ch1.md", doc, out, _SETTINGS)
    assert not can_reuse({}, "ch1.md", doc, out, _SETTINGS)  # no record
    doc.write_text("# One\nEdited.", encoding="utf-8")
    assert not can_reuse(entries, "ch1.md", doc, out, _SETTINGS)  # text changed

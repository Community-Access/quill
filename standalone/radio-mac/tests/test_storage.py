"""Tests for quill_radio_mac.core.storage.

Exercises the atomic JSON writer: fresh writes, overwrite of an
existing file (content fully replaced), cleanliness of the target
directory afterwards (no leftover .tmp files), and the base-directory
escape guard. Pure filesystem tests against tmp_path; no network,
no wx.
"""

from __future__ import annotations

import json

import pytest

from quill_radio_mac.core.storage import (
    PathEscapeError,
    resolve_within,
    write_json_atomic,
)


def test_write_json_atomic_creates_file_and_parents(tmp_path):
    target = tmp_path / "nested" / "deeper" / "settings.json"
    write_json_atomic(target, {"volume": 80})
    assert json.loads(target.read_text(encoding="utf-8")) == {"volume": 80}


def test_write_json_atomic_replaces_existing_content(tmp_path):
    target = tmp_path / "radio_favorites.json"
    write_json_atomic(target, {"stations": ["old"], "extra": True})
    write_json_atomic(target, {"stations": ["new"]})
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data == {"stations": ["new"]}
    assert "extra" not in data


def test_write_json_atomic_leaves_no_tmp_files(tmp_path):
    target = tmp_path / "radio_history.json"
    write_json_atomic(target, {"recents": []})
    write_json_atomic(target, {"recents": [1, 2, 3]})
    leftovers = [p for p in tmp_path.iterdir() if p.name != target.name]
    assert leftovers == []


def test_write_json_atomic_round_trips_unicode(tmp_path):
    # Escapes keep this source file ASCII-only while still exercising
    # ensure_ascii=False round-tripping of non-ASCII station names.
    target = tmp_path / "unicode.json"
    payload = {"name": "Radio Reci\u0161ka", "tags": ["\u010de\u0161tina"]}
    write_json_atomic(target, payload)
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_write_json_atomic_honors_base_guard(tmp_path):
    base = tmp_path / "appdata"
    base.mkdir()
    inside = base / "ok.json"
    write_json_atomic(inside, {"fine": 1}, base=base)
    assert inside.exists()
    outside = tmp_path / "escape.json"
    with pytest.raises(PathEscapeError):
        write_json_atomic(outside, {"bad": 1}, base=base)
    assert not outside.exists()


def test_resolve_within_accepts_base_itself(tmp_path):
    assert resolve_within(tmp_path, tmp_path) == tmp_path.resolve()


def test_resolve_within_rejects_dotdot_escape(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(PathEscapeError):
        resolve_within(base, base / ".." / "elsewhere.json")

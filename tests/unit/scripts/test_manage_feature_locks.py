"""Tests for the owner's feature-lock management tool (pure feed ops)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "manage_feature_locks", _ROOT / "scripts" / "manage_feature_locks.py"
)
assert _spec and _spec.loader
mfl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mfl)

from quill.core.updates import active_feature_locks, parse_update_manifest  # noqa: E402

_URL = "https://github.com/Community-Access/quill/releases/download/latest/x.exe"


def _base_feed() -> dict:
    feed = {"version": "0.9.0", "download_url": _URL, "published_at": "", "notes": ""}
    return mfl.resign(feed)


def test_base_feed_verifies() -> None:
    parse_update_manifest(json.dumps(_base_feed()))  # no advisories, valid signature


def test_add_lock_signs_and_resolves() -> None:
    feed = mfl.add_lock(_base_feed(), "core.glow", reason="crash", max_version="0.9.5")
    manifest = parse_update_manifest(json.dumps(feed))  # signature covers the advisory
    assert active_feature_locks(manifest, "0.9.0") == {"core.glow": "crash"}
    assert active_feature_locks(manifest, "0.9.9") == {}  # past max_version


def test_add_is_idempotent_per_feature() -> None:
    feed = mfl.add_lock(_base_feed(), "core.glow", reason="first")
    feed = mfl.add_lock(feed, "core.glow", reason="second")  # replaces, not duplicates
    assert len(mfl.list_locks(feed)) == 1
    assert mfl.list_locks(feed)[0]["reason"] == "second"


def test_remove_lock_restores_backward_compatible_shape() -> None:
    feed = mfl.add_lock(_base_feed(), "core.glow", reason="crash")
    feed = mfl.remove_lock(feed, "core.glow")
    assert "advisories" not in feed  # no-advisory feed keeps the old signed shape
    parse_update_manifest(json.dumps(feed))  # still verifies


def test_render_locks_is_speakable() -> None:
    assert "No features" in mfl.render_locks(_base_feed())
    feed = mfl.add_lock(_base_feed(), "core.glow", reason="crash", max_version="0.9.5")
    text = mfl.render_locks(feed)
    assert "core.glow" in text and "crash" in text


def test_save_feed_round_trip(tmp_path) -> None:
    path = tmp_path / "feed.json"
    feed = mfl.add_lock(_base_feed(), "core.ai.x", reason="bug")
    mfl.save_feed(path, feed)  # raises if it doesn't verify
    reloaded = mfl.load_feed(path)
    assert mfl.list_locks(reloaded)[0]["feature_id"] == "core.ai.x"

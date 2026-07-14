"""Tests for the remote feature kill switch persistence + enforcement state."""

from __future__ import annotations

import pytest

from quill.core.safety import feature_lock
from quill.core.safety.feature_lock import (
    FeatureLockState,
    apply_manifest_locks,
    load_feature_locks,
    locks_ignored,
    save_feature_locks,
)
from quill.core.updates import FeatureAdvisory, UpdateManifest


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("QUILL_IGNORE_FEATURE_LOCKS", raising=False)
    yield


def test_state_is_locked_and_reason() -> None:
    state = FeatureLockState(locked={"core.glow": "crash"})
    assert state.is_locked("core.glow") is True
    assert state.is_locked("core.other") is False
    assert state.reason("core.glow") == "crash"


def test_escape_hatch_disables_all_locks(monkeypatch) -> None:
    state = FeatureLockState(locked={"core.glow": "crash"})
    monkeypatch.setenv("QUILL_IGNORE_FEATURE_LOCKS", "1")
    assert locks_ignored() is True
    assert state.is_locked("core.glow") is False  # honored escape hatch
    assert state.active() == {}


def test_save_and_load_round_trip() -> None:
    save_feature_locks({"core.glow": "crash", "core.ai.x": "bug"})
    loaded = load_feature_locks()
    assert loaded.locked == {"core.glow": "crash", "core.ai.x": "bug"}


def test_load_missing_cache_is_empty() -> None:
    assert load_feature_locks().locked == {}


def test_load_corrupt_cache_is_empty() -> None:
    path = feature_lock._state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")
    assert load_feature_locks().locked == {}  # degrades, never raises


def test_apply_manifest_locks_persists_and_resolves() -> None:
    manifest = UpdateManifest(
        version="0.9.0",
        download_url="x",
        published_at="",
        notes="",
        signature="",
        advisories=(FeatureAdvisory(feature_id="core.glow", reason="crash", max_version="0.9.5"),),
    )
    state = apply_manifest_locks(manifest, "0.9.0")
    assert state.is_locked("core.glow")
    # Persisted, so the next launch (a fresh load) still honors it — even offline.
    assert load_feature_locks().locked == {"core.glow": "crash"}


def test_apply_empty_manifest_clears_prior_locks() -> None:
    save_feature_locks({"core.glow": "old"})
    manifest = UpdateManifest(
        version="0.9.0", download_url="x", published_at="", notes="", signature="", advisories=()
    )
    state = apply_manifest_locks(manifest, "0.9.0")
    assert state.locked == {}  # a fixed build's manifest lifts the kill switch
    assert load_feature_locks().locked == {}


def test_apply_lifts_lock_when_version_moves_past_max() -> None:
    manifest = UpdateManifest(
        version="0.9.9",
        download_url="x",
        published_at="",
        notes="",
        signature="",
        advisories=(FeatureAdvisory(feature_id="core.glow", reason="crash", max_version="0.9.5"),),
    )
    # The running build (0.9.9) is past the advisory's max_version, so nothing locks.
    assert apply_manifest_locks(manifest, "0.9.9").locked == {}


# -- dependency cascade (a lock disables everything built on it) --------------


def test_locking_a_parent_cascades_to_dependents() -> None:
    # core.format depends on core.editor; locking the editor must lock the
    # dependent, with the parent's reason.
    state = FeatureLockState(locked={"core.editor": "editor bug"})
    assert state.is_locked("core.editor") is True
    assert state.is_locked("core.format") is True  # depends on core.editor
    assert state.reason("core.format") == "editor bug"
    assert state.is_locked("core.window") is False  # unrelated feature


def test_cascade_is_transitive() -> None:
    # core.app <- core.editor <- core.format; locking the root locks the leaf.
    state = FeatureLockState(locked={"core.app": "root outage"})
    assert state.is_locked("core.format") is True
    assert state.reason("core.format") == "root outage"


def test_escape_hatch_disables_cascade_too(monkeypatch) -> None:
    state = FeatureLockState(locked={"core.editor": "bug"})
    monkeypatch.setenv("QUILL_IGNORE_FEATURE_LOCKS", "1")
    assert state.is_locked("core.format") is False
    assert state.reason("core.format") == ""


def test_active_reports_only_directly_locked() -> None:
    # active() is the operator's explicit set (for the count/notice), not the
    # full cascaded set.
    state = FeatureLockState(locked={"core.editor": "bug"})
    assert state.active() == {"core.editor": "bug"}

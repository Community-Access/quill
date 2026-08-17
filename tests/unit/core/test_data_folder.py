"""The Data Folder feature: synced custom folders, machine-local caches,
the two-machines heartbeat, and every app applying a queued move.

The #615 machinery (storage-mode.json, the restart-deferred move) predates
this; what is pinned here is the 2026-08-17 surfacing: standalone apps
apply pending moves at launch, caches stay off the synced folder, and a
profile in use on another computer says so instead of silently splitting.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from quill.core import paths, profile_heartbeat

# --- machine-local caches -------------------------------------------------------


def test_machine_local_dir_follows_the_dev_override(monkeypatch, tmp_path) -> None:
    # Tests (and dev runs) isolate everything under one QUILL_DATA_DIR.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert paths.machine_local_dir() == paths.app_data_dir()


def test_machine_local_dir_leaves_a_synced_custom_folder(monkeypatch, tmp_path) -> None:
    # A custom folder exists to be synced; caches must not ride along.
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setattr(paths, "load_storage_mode", lambda: "custom")
    monkeypatch.setattr(paths.storage_mode, "custom_path", lambda: tmp_path / "dropbox" / "Quill")
    local = paths.machine_local_dir()
    assert local == tmp_path / "appdata" / "Quill" / "machine-cache"
    assert "dropbox" not in str(local)


def test_machine_local_dir_is_the_data_dir_for_appdata_and_portable(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    for mode in ("appdata", "portable", None):
        monkeypatch.setattr(paths, "load_storage_mode", lambda m=mode: m)
        assert paths.machine_local_dir() == paths.app_data_dir()


# --- the two-machines heartbeat -------------------------------------------------


def _stamp(tmp_path: Path, *, machine: str, age_seconds: float) -> None:
    (tmp_path / "profile-heartbeat.json").write_text(
        json.dumps({"machine": machine, "pid": 1, "at": time.time() - age_seconds}),
        encoding="utf-8",
    )


def test_a_fresh_foreign_stamp_warns_and_names_the_machine(tmp_path) -> None:
    _stamp(tmp_path, machine="LAPTOP-ELSEWHERE", age_seconds=120)
    warning = profile_heartbeat.foreign_use_warning(tmp_path)
    assert "LAPTOP-ELSEWHERE" in warning
    assert "two computers" in warning


def test_our_own_stamp_never_warns(tmp_path) -> None:
    profile_heartbeat.note_profile_use(tmp_path)
    assert profile_heartbeat.foreign_use_warning(tmp_path) == ""


def test_a_stale_foreign_stamp_is_quiet(tmp_path) -> None:
    _stamp(tmp_path, machine="LAPTOP-ELSEWHERE", age_seconds=3600)
    assert profile_heartbeat.foreign_use_warning(tmp_path) == ""


def test_no_stamp_and_garbage_stamps_are_quiet(tmp_path) -> None:
    assert profile_heartbeat.foreign_use_warning(tmp_path) == ""
    (tmp_path / "profile-heartbeat.json").write_text("{not json", encoding="utf-8")
    assert profile_heartbeat.foreign_use_warning(tmp_path) == ""


def test_startup_guard_warns_then_takes_over_the_stamp(tmp_path) -> None:
    _stamp(tmp_path, machine="LAPTOP-ELSEWHERE", age_seconds=120)
    warning = profile_heartbeat.startup_profile_guard(tmp_path)
    assert "LAPTOP-ELSEWHERE" in warning
    # The stamp is now ours, so the next check is quiet.
    assert profile_heartbeat.foreign_use_warning(tmp_path) == ""


def test_refresh_is_throttled_so_a_synced_folder_is_not_churned(tmp_path) -> None:
    profile_heartbeat.note_profile_use(tmp_path)
    stamp_path = tmp_path / "profile-heartbeat.json"
    before = stamp_path.read_text(encoding="utf-8")
    profile_heartbeat.refresh_profile_use(tmp_path)  # fresh: must not rewrite
    assert stamp_path.read_text(encoding="utf-8") == before
    _stamp(
        tmp_path,
        machine=json.loads(before)["machine"],
        age_seconds=profile_heartbeat.REFRESH_SECONDS + 60,
    )
    profile_heartbeat.refresh_profile_use(tmp_path)  # old: rewritten
    assert json.loads(stamp_path.read_text(encoding="utf-8"))["at"] > time.time() - 60


# --- every app applies a queued move at launch ----------------------------------


def test_apply_pending_at_launch_runs_both_applies_in_order(monkeypatch) -> None:
    from quill.core import data_location

    calls: list[str] = []
    monkeypatch.setattr(
        data_location,
        "apply_pending_data_location_migration",
        lambda: calls.append("move"),
    )
    monkeypatch.setattr(
        data_location, "apply_pending_legacy_import", lambda: calls.append("import")
    )
    data_location.apply_pending_at_launch()
    assert calls == ["move", "import"]  # same order as quill.__main__.main


def test_every_app_main_applies_pending_moves() -> None:
    """A queued Data Folder change must apply from whichever app launches
    next -- the family shares one profile. An app main() that skips the call
    strands the move until QUILL itself happens to run."""
    apps_dir = Path(paths.__file__).resolve().parents[1] / "apps"
    missing = []
    for source in sorted(apps_dir.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        if "\ndef main() -> int:" not in text:
            continue
        if "apply_pending_at_launch" not in text:
            missing.append(source.name)
    assert not missing, f"app mains missing apply_pending_at_launch: {missing}"

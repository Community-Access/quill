"""Shared Python runtime reference counting -- dedup/GC of the shared runtime."""

from __future__ import annotations

from pathlib import Path

from quill.core import runtime_refs as r


def test_register_running_app_writes_to_the_shared_data_dir(tmp_path: Path, monkeypatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    r.register_running_app("radio", "3.13.1")
    assert r.apps_requiring(tmp_path, "3.13.1") == ["radio"]


def test_register_running_app_never_raises_on_bad_data_dir(monkeypatch) -> None:
    import quill.core.paths as paths

    def _boom() -> Path:
        raise RuntimeError("no APPDATA")

    monkeypatch.setattr(paths, "app_data_dir", _boom)
    r.register_running_app("radio", "3.13.1")  # must not raise -- launch guard


def test_apps_share_one_runtime_version(tmp_path: Path) -> None:
    r.register(tmp_path, "radio", "3.13.1")
    r.register(tmp_path, "cast", "3.13.1")
    r.register(tmp_path, "studio", "3.13.1")
    assert r.apps_requiring(tmp_path, "3.13.1") == ["cast", "radio", "studio"]  # deduped, sorted
    assert r.is_referenced(tmp_path, "3.13.1")


def test_upgrade_moves_an_app_between_versions(tmp_path: Path) -> None:
    r.register(tmp_path, "radio", "3.13.1")
    r.register(tmp_path, "cast", "3.13.1")
    # Radio upgrades onto a newer runtime; its old ref is dropped, cast keeps 3.13.1.
    r.register(tmp_path, "radio", "3.14.0")
    assert r.apps_requiring(tmp_path, "3.14.0") == ["radio"]
    assert r.apps_requiring(tmp_path, "3.13.1") == ["cast"]


def test_register_is_idempotent(tmp_path: Path) -> None:
    r.register(tmp_path, "radio", "3.13.1")
    r.register(tmp_path, "radio", "3.13.1")  # re-launch: no change
    assert r.apps_requiring(tmp_path, "3.13.1") == ["radio"]


def test_unregister_removes_all_of_an_apps_refs(tmp_path: Path) -> None:
    r.register(tmp_path, "radio", "3.13.1")
    r.register(tmp_path, "cast", "3.13.1")
    r.unregister(tmp_path, "radio")  # the radio uninstaller
    assert r.apps_requiring(tmp_path, "3.13.1") == ["cast"]


def test_unreferenced_lists_only_removable_runtimes(tmp_path: Path) -> None:
    r.register(tmp_path, "radio", "3.13.1")
    assert r.unreferenced(tmp_path, ["3.13.1", "3.12.7", "3.14.0"]) == ["3.12.7", "3.14.0"]


def test_state_persists_and_stays_tidy(tmp_path: Path) -> None:
    r.register(tmp_path, "radio", "3.13.1")
    assert (tmp_path / "runtime.state.json").is_file()
    r.unregister(tmp_path, "radio")
    import json

    payload = json.loads((tmp_path / "runtime.state.json").read_text(encoding="utf-8"))
    assert payload == {"refs": {}}  # empty versions dropped, no junk

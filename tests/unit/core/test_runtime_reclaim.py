"""Reclaiming an older Python's runtime slot (quill.core.runtime_reclaim).

Removing a runtime an app still needs stops that app starting, so most of these
pin a reason to KEEP a slot; the removal itself goes through a fake.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import runtime_cli, runtime_reclaim, runtime_refs
from quill.core.runtime_reclaim import (
    InstallScan,
    older_slots,
    reclaim,
    scan_installs,
    slots_launched_by,
    slots_named_by_installs,
)


def _slots(root: Path, *names: str) -> None:
    for name in names:
        (root / name).mkdir(parents=True)


def _app(base: Path, name: str, ini: str, *, private: bool = False) -> Path:
    app = base / name
    app.mkdir(parents=True)
    (app / "quill-app-version.ini").write_text(ini, encoding="utf-8")
    if private:
        (app / "_internal").mkdir()
        (app / "_internal" / "python.exe").write_bytes(b"")
    return app


class _Remover:
    def __init__(self, *, succeeds: bool = True) -> None:
        self.removed: list[str] = []
        self.succeeds = succeeds

    def __call__(self, slot_dir: Path, slot: str) -> bool:
        self.removed.append(slot)
        return self.succeeds


def test_only_an_older_pythons_slots_are_candidates(tmp_path: Path) -> None:
    _slots(tmp_path, "3.13", "3.13-beta", "3.13-dev", "3.14", "3.14-beta", "3.15", "junk")
    (tmp_path / "3.12").write_text("a file, not a slot")
    assert older_slots(tmp_path, "3.14") == ["3.13", "3.13-beta", "3.13-dev"]
    assert older_slots(tmp_path, "3.14-beta") == ["3.13", "3.13-beta", "3.13-dev"]
    assert older_slots(tmp_path, "not a slot") == []
    assert older_slots(tmp_path / "missing", "3.14") == []


def test_an_unused_old_slot_is_removed(tmp_path: Path) -> None:
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13", "3.14")
    data.mkdir()
    runtime_refs.register(data, "radio", "3.14")
    app = _app(tmp_path / "apps", "radio", "[runtime]\nslot=3.14\n")
    remover = _Remover()
    results = reclaim(data, root, "3.14", InstallScan([app], False), [], remove=remover)
    assert remover.removed == ["3.13"]
    assert [(r.slot, r.action) for r in results] == [("3.13", "removed")]


def test_a_registered_app_keeps_its_slot(tmp_path: Path) -> None:
    """Apps register at every launch, so an un-updated 3.13 app that has run
    keeps 3.13 -- including under the old full-version key ("3.13.1")."""
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13")
    data.mkdir()
    runtime_refs.register(data, "weather", "3.13.1")
    remover = _Remover()
    results = reclaim(data, root, "3.14", InstallScan([], False), [], remove=remover)
    assert remover.removed == []
    assert results[0].action == "kept"


def test_an_installed_apps_ini_keeps_its_slot(tmp_path: Path) -> None:
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13-beta")
    data.mkdir()
    app = _app(tmp_path / "apps", "cast", "[runtime]\nslot=3.13-beta\n")
    remover = _Remover()
    reclaim(data, root, "3.14", InstallScan([app], False), [], remove=remover)
    assert remover.removed == []


def test_an_ini_without_slot_keeps_every_older_stable_slot(tmp_path: Path) -> None:
    """An install from before release channels runs on the Python its launcher
    was built for. Its Beta and Dev slots were never that app's, so they go."""
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13", "3.13-beta")
    data.mkdir()
    app = _app(tmp_path / "apps", "lite", "[app]\nversion=1.1.2\n")
    remover = _Remover()
    results = {
        r.slot: r.action
        for r in reclaim(data, root, "3.14", InstallScan([app], False), [], remove=remover)
    }
    assert results == {"3.13": "kept", "3.13-beta": "removed"}


@pytest.mark.parametrize("ini", ["[runtime]\nslot=..\\..\\Windows\n", "not an ini at all ["])
def test_an_unreadable_or_bad_slot_counts_as_unknown(tmp_path: Path, ini: str) -> None:
    app = _app(tmp_path, "app", ini)
    assert slots_named_by_installs([app]) == (set(), True)


def test_an_app_with_its_own_runtime_is_ignored(tmp_path: Path) -> None:
    app = _app(tmp_path, "quill", "[app]\nversion=1.0.0\n", private=True)
    assert slots_named_by_installs([app]) == (set(), False)


def test_a_failed_removal_is_reported_as_kept(tmp_path: Path) -> None:
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13")
    data.mkdir()
    results = reclaim(
        data, root, "3.14", InstallScan([], False), [], remove=_Remover(succeeds=False)
    )
    assert results[0].action == "kept"


def test_the_real_removal_deletes_the_folder(tmp_path: Path) -> None:
    slot_dir = tmp_path / "3.13"
    (slot_dir / "Lib").mkdir(parents=True)
    (slot_dir / "Lib" / "x.py").write_text("")
    assert runtime_reclaim._remove_slot(slot_dir, "3.13") is True
    assert not slot_dir.exists()


def test_the_cli_reports_and_never_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13", "3.14")
    data.mkdir()
    monkeypatch.setattr(runtime_cli, "_data_dir", lambda: data)
    monkeypatch.setattr(runtime_reclaim, "runtime_root", lambda: root)
    monkeypatch.setattr(runtime_reclaim, "scan_installs", lambda: InstallScan([], False))
    monkeypatch.setattr(runtime_reclaim, "launch_references", lambda: [])
    assert runtime_cli.main(["reclaim-old-slots", "3.14"]) == 0
    assert "3.13 removed" in capsys.readouterr().out
    assert not (root / "3.13").exists() and (root / "3.14").exists()
    assert runtime_cli.main(["reclaim-old-slots"]) == 2


def test_every_app_installer_reclaims_after_registering() -> None:
    fragment = (Path(__file__).resolve().parents[3] / "installer" / "shared-runtime.iss").read_text(
        encoding="utf-8"
    )
    register = fragment.index("runtime_cli register {#AppRefId} {code:RuntimeSlot}")
    reclaim_at = fragment.index("runtime_cli reclaim-old-slots {code:RuntimeSlot}")
    assert register < reclaim_at


def test_a_shortcut_that_runs_from_a_slot_keeps_it(tmp_path: Path) -> None:
    """The earliest installers had no ini and pointed the Start menu straight at
    Runtime/3.13/QuillVilleRuntime.exe -m quill.apps.radio. That shortcut still
    works -- the runtime carries the app -- so the slot stays (a real machine,
    2026-10-12, whose Radio 3.0.0 install folder was long gone)."""
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13", "3.13-beta")
    data.mkdir()
    target = str(root / "3.13" / "QuillVilleRuntime.exe")
    lnk = b"L\x00\x00\x00junk" + target.encode("utf-16-le") + b"\x00\x00-m quill.apps.radio"
    remover = _Remover()
    results = {
        r.slot: r.action
        for r in reclaim(data, root, "3.14", InstallScan([], False), [lnk], remove=remover)
    }
    assert results == {"3.13": "kept", "3.13-beta": "removed"}


def test_shortcut_matching_is_by_folder_not_prefix(tmp_path: Path) -> None:
    root = tmp_path / "Runtime"
    beta = str(root / "3.13-beta" / "QuillVilleRuntime.exe").upper().encode("latin-1")
    assert slots_launched_by(root, ["3.13", "3.13-beta"], [beta]) == {"3.13-beta"}


def test_an_old_install_without_an_ini_keeps_stable_slots(tmp_path: Path) -> None:
    old = tmp_path / "Quill Radio"
    old.mkdir()
    (old / "QuillRadio.exe").write_bytes(b"")
    gone = tmp_path / "removed long ago"
    scan = scan_installs([
        (str(old), "Community Access"),
        (f'"{gone}"', "Community Access"),
        (str(tmp_path), "Someone Else"),
    ])
    assert scan == InstallScan([], True)
    root, data = tmp_path / "Runtime", tmp_path / "data"
    _slots(root, "3.13", "3.13-dev")
    data.mkdir()
    results = {r.slot: r.action for r in reclaim(data, root, "3.14", scan, [], remove=_Remover())}
    assert results == {"3.13": "kept", "3.13-dev": "removed"}

"""The build-machine fingerprint: capture is read-only, compare names the drift.

Two checkouts at the same commit can produce installers tens of megabytes apart,
because ``collect_all("quill")`` sweeps whatever is importable on the machine
that runs it. ``check_build_env.py`` guards the floor and
``check_runtime_inventory.py`` the ceiling; neither answers "what is different
between these two machines". These tests pin the tool that does: that a capture
touches nothing, that a package present on one side only is reported, that a
staged binary whose bytes differ is reported as differing rather than as equal
sizes, and that two identical fingerprints produce no drift.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_fingerprint.py"
_spec = importlib.util.spec_from_file_location("build_fingerprint", _SCRIPT)
assert _spec is not None and _spec.loader is not None
fingerprint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fingerprint)


def _fake(label: str, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema": 1,
        "label": label,
        "repo": "S:/QUILL",
        "git": {"commit": "abc123", "branch": "main", "dirty": False, "changed_files": 0},
        "interpreter": {
            "executable": "python.exe",
            "version": "3.13.15",
            "implementation": "CPython",
            "externally_managed": False,
            "os": "Windows 11 (AMD64)",
        },
        "packages": {"wxpython": "4.3.1", "pypdf": "6.16.1"},
        "staged_binaries": {
            "build/deps/ffmpeg/ffmpeg.exe": {"bytes": 100, "sha256": "a" * 64},
        },
        "runtime": {
            "total_bytes": 1000,
            "_internal": {"enchant": 900, "wx": 100},
            "tools": {"ffmpeg": 0},
        },
        "artifacts": {"standalone/radio/dist/Quill-Radio-Setup-Shared-3.0.0.exe": 500},
    }
    base.update(overrides)
    return base


def test_capture_writes_a_schema_1_fingerprint_and_changes_nothing(tmp_path: Path) -> None:
    repo = tmp_path / "checkout"
    (repo / "build" / "deps").mkdir(parents=True)
    before = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*"))

    data = fingerprint.capture(repo, "unit")

    assert data["schema"] == 1
    assert data["label"] == "unit"
    # Every section is present even though this "checkout" has none of it.
    assert data["runtime"] is None
    assert data["artifacts"] == {}
    assert set(data["staged_binaries"]) == set(fingerprint._STAGED_BINARIES)
    assert all(value is None for value in data["staged_binaries"].values())
    # Read-only: the walk created nothing.
    assert sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*")) == before


def test_capture_records_size_and_hash_of_a_staged_binary(tmp_path: Path) -> None:
    repo = tmp_path / "checkout"
    staged = repo / "build" / "deps" / "ffmpeg"
    staged.mkdir(parents=True)
    (staged / "ffmpeg.exe").write_bytes(b"pinned bytes")

    data = fingerprint.capture(repo, "unit")

    entry = data["staged_binaries"]["build/deps/ffmpeg/ffmpeg.exe"]
    assert entry["bytes"] == len(b"pinned bytes")
    assert len(entry["sha256"]) == 64


def test_identical_fingerprints_report_no_drift(capsys) -> None:
    drift = fingerprint.compare(_fake("work"), _fake("home"))
    out = capsys.readouterr().out

    assert "identical." in out  # packages
    assert "difference: none" in out  # runtime total
    assert "DIFFERENT BYTES" not in out
    assert drift == 0


def test_a_package_on_one_side_only_is_named(capsys) -> None:
    stray = _fake("home", packages={"wxpython": "4.3.1", "pypdf": "6.16.1", "pymupdf": "1.26.0"})

    fingerprint.compare(_fake("work"), stray)
    out = capsys.readouterr().out

    assert "only on home" in out
    assert "pymupdf 1.26.0" in out


def test_a_version_difference_is_named_with_both_versions(capsys) -> None:
    older = _fake("home", packages={"wxpython": "4.3.1", "pypdf": "6.15.0"})

    fingerprint.compare(_fake("work"), older)
    out = capsys.readouterr().out

    assert "pypdf: work 6.16.1 vs home 6.15.0" in out


def test_same_size_different_bytes_is_not_reported_as_identical(capsys) -> None:
    """A hand-built ffmpeg can match the pinned one's size and not its content."""
    impostor = _fake(
        "home",
        staged_binaries={"build/deps/ffmpeg/ffmpeg.exe": {"bytes": 100, "sha256": "b" * 64}},
    )

    fingerprint.compare(_fake("work"), impostor)
    out = capsys.readouterr().out

    assert "DIFFERENT BYTES" in out


def test_runtime_item_size_delta_is_reported(capsys) -> None:
    pruned = _fake(
        "home",
        runtime={
            "total_bytes": 200,
            "_internal": {"enchant": 100, "wx": 100},
            "tools": {"ffmpeg": 0},
        },
    )

    fingerprint.compare(_fake("work"), pruned)
    out = capsys.readouterr().out

    assert "enchant" in out
    assert "larger on work" in out


def test_a_missing_runtime_on_one_side_is_explained_not_crashed(capsys) -> None:
    drift = fingerprint.compare(_fake("work"), _fake("home", runtime=None))
    out = capsys.readouterr().out

    assert "no built runtime on: home" in out
    # A fresh clone has no runtime by design; absence of data is not drift.
    assert drift == 0


def test_round_trips_through_json(tmp_path: Path) -> None:
    path = tmp_path / "work.json"
    path.write_text(json.dumps(_fake("work")), encoding="utf-8")

    assert fingerprint._load(path)["label"] == "work"


def test_machine_identity_differences_are_not_drift(capsys) -> None:
    """Commit, branch, dirty state, interpreter path and OS always differ across
    two real machines; counting them would make --fail-on-drift always fire."""
    other = _fake(
        "home",
        git={"commit": "def456", "branch": "feature", "dirty": True, "changed_files": 3},
        interpreter={
            "executable": r"C:\Users\other\python.exe",
            "version": "3.13.15",
            "implementation": "CPython",
            "externally_managed": False,
            "os": "Windows 11 (ARM64)",
        },
    )

    assert fingerprint.compare(_fake("work"), other) == 0
    assert "<-- differs" in capsys.readouterr().out  # reported, just not counted


def test_ship_affecting_differences_are_each_counted(capsys) -> None:
    other = _fake(
        "home",
        packages={"wxpython": "4.3.1"},  # pypdf gone: 1
        staged_binaries={
            "build/deps/ffmpeg/ffmpeg.exe": {"bytes": 100, "sha256": "b" * 64},  # 1
        },
        artifacts={"standalone/radio/dist/Quill-Radio-Setup-Shared-3.0.0.exe": 999},  # 1
        runtime={
            "total_bytes": 900,
            "_internal": {"enchant": 800, "wx": 100},  # enchant differs: 1
            "tools": {"ffmpeg": 0},
        },
    )

    drift = fingerprint.compare(_fake("work"), other)
    out = capsys.readouterr().out

    assert drift == 4
    assert "4 difference(s) that can change what a build ships." in out


def test_fail_on_drift_flag_controls_the_exit_code(tmp_path: Path, monkeypatch, capsys) -> None:
    left = tmp_path / "work.json"
    right = tmp_path / "home.json"
    left.write_text(json.dumps(_fake("work")), encoding="utf-8")
    right.write_text(json.dumps(_fake("home", packages={"wxpython": "4.3.1"})), encoding="utf-8")

    argv = ["build_fingerprint.py", "compare", str(left), str(right)]
    monkeypatch.setattr(sys, "argv", argv)
    assert fingerprint.main() == 0  # drifted, but a human is reading: exit 0

    monkeypatch.setattr(sys, "argv", [*argv, "--fail-on-drift"])
    assert fingerprint.main() == 1

    right.write_text(json.dumps(_fake("home")), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [*argv, "--fail-on-drift"])
    assert fingerprint.main() == 0  # identical: the flag alone never fails


def test_capture_finds_the_main_quill_installer_but_not_build_internals(tmp_path: Path) -> None:
    """dist/windows holds the portable zip at the top and Setup.exe under
    installer/Output; the portable/ tree beside them is build payload."""
    repo = tmp_path / "checkout"
    output = repo / "dist" / "windows" / "installer" / "Output"
    output.mkdir(parents=True)
    portable = repo / "dist" / "windows" / "portable"
    portable.mkdir(parents=True)
    (repo / "dist" / "windows" / "Quill-Portable-1.0.0.zip").write_bytes(b"portable zip")
    (output / "Quill-for-All-Setup-1.0.0.exe").write_bytes(b"setup exe")
    (portable / "python313.zip").write_bytes(b"embedded stdlib, not an artifact")

    artifacts = fingerprint.capture(repo, "unit")["artifacts"]

    assert "dist/windows/Quill-Portable-1.0.0.zip" in artifacts
    assert "dist/windows/installer/Output/Quill-for-All-Setup-1.0.0.exe" in artifacts
    assert not any("python313" in name for name in artifacts)

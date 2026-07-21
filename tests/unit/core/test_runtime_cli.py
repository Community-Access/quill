"""Installer-facing CLI for shared-runtime reference counting."""

from __future__ import annotations

from pathlib import Path

from quill.core import runtime_cli, runtime_refs


def _point_data_dir(monkeypatch, tmp_path: Path) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)


def test_register_records_the_ref(monkeypatch, tmp_path: Path) -> None:
    _point_data_dir(monkeypatch, tmp_path)
    assert runtime_cli.main(["register", "radio", "3.13.1"]) == 0
    assert runtime_refs.apps_requiring(tmp_path, "3.13.1") == ["radio"]


def test_unregister_last_app_signals_removable(monkeypatch, tmp_path: Path) -> None:
    _point_data_dir(monkeypatch, tmp_path)
    runtime_cli.main(["register", "radio", "3.13.1"])
    # Only app on this runtime -> exit 10 tells the installer it may delete it.
    assert runtime_cli.main(["unregister", "radio", "3.13.1"]) == 10


def test_unregister_keeps_runtime_when_others_remain(monkeypatch, tmp_path: Path) -> None:
    _point_data_dir(monkeypatch, tmp_path)
    runtime_cli.main(["register", "radio", "3.13.1"])
    runtime_cli.main(["register", "cast", "3.13.1"])
    # cast still needs it -> exit 0 (do not remove the shared runtime).
    assert runtime_cli.main(["unregister", "radio", "3.13.1"]) == 0
    assert runtime_refs.apps_requiring(tmp_path, "3.13.1") == ["cast"]


def test_is_referenced_exit_codes(monkeypatch, tmp_path: Path) -> None:
    _point_data_dir(monkeypatch, tmp_path)
    assert runtime_cli.main(["is-referenced", "3.13.1"]) == 10  # nothing needs it
    runtime_cli.main(["register", "radio", "3.13.1"])
    assert runtime_cli.main(["is-referenced", "3.13.1"]) == 0


def test_data_dir_prints(monkeypatch, tmp_path: Path, capsys) -> None:
    _point_data_dir(monkeypatch, tmp_path)
    assert runtime_cli.main(["data-dir"]) == 0
    assert str(tmp_path) in capsys.readouterr().out


def test_usage_and_unknown_return_2(monkeypatch, tmp_path: Path) -> None:
    _point_data_dir(monkeypatch, tmp_path)
    assert runtime_cli.main([]) == 2
    assert runtime_cli.main(["register", "radio"]) == 2  # missing version
    assert runtime_cli.main(["frobnicate"]) == 2


def test_never_raises_to_the_installer(monkeypatch) -> None:
    import quill.core.paths as paths

    def _boom() -> Path:
        raise RuntimeError("no APPDATA")

    monkeypatch.setattr(paths, "app_data_dir", _boom)
    # A broken data dir must surface as a non-zero exit, not a traceback.
    assert runtime_cli.main(["register", "radio", "3.13.1"]) == 1

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


# -- heal-launch-entries ------------------------------------------------------
#
# The installer's repair of a "start with Windows" entry an older build wrote as
# the bare runtime exe. The app heals its own entry at launch, but the broken
# entry is the one that prevents launches, so the installer does it too.


def test_heal_runs_every_app_healer_and_reports_the_count(monkeypatch, capsys) -> None:
    called: list[str] = []

    def _healer(name: str, answer: bool):
        def _heal() -> bool:
            called.append(name)
            return answer

        return _heal

    monkeypatch.setattr(
        runtime_cli,
        "_STARTUP_HEALERS",
        (("mod.radio", "heal"), ("mod.weather", "heal"), ("mod.inkwell", "heal")),
    )
    modules = {
        "mod.radio": _healer("radio", True),
        "mod.weather": _healer("weather", False),
        "mod.inkwell": _healer("inkwell", True),
    }

    import importlib

    def _import(name: str):
        return type("M", (), {"heal": staticmethod(modules[name])})

    monkeypatch.setattr(importlib, "import_module", _import)
    assert runtime_cli.main(["heal-launch-entries"]) == 0
    assert called == ["radio", "weather", "inkwell"]
    # Two of the three had an entry to rewrite; the third had none.
    assert "repaired 2" in capsys.readouterr().out


def test_a_healer_that_raises_never_fails_the_install(monkeypatch, capsys) -> None:
    monkeypatch.setattr(runtime_cli, "_STARTUP_HEALERS", (("mod.boom", "heal"),))

    import importlib

    def _import(name: str):
        raise ImportError("no such module")

    monkeypatch.setattr(importlib, "import_module", _import)
    # A locked-down registry or a missing module costs the repair, not the install.
    assert runtime_cli.main(["heal-launch-entries"]) == 0
    assert "skipped" in capsys.readouterr().out


def test_the_launcher_directory_is_exported_for_app_command(monkeypatch, absent_env) -> None:
    """The repaired entry must name the app's launcher, not the runtime's
    versioned path -- which is what survives the next runtime upgrade."""
    import os

    absent_env("QUILL_LAUNCHER_DIR")
    monkeypatch.setattr(runtime_cli, "_STARTUP_HEALERS", ())
    assert runtime_cli.main(["heal-launch-entries", r"C:\Program Files\Quill Radio"]) == 0
    assert os.environ["QUILL_LAUNCHER_DIR"] == r"C:\Program Files\Quill Radio"


def test_no_launcher_directory_leaves_the_environment_alone(monkeypatch, absent_env) -> None:
    import os

    absent_env("QUILL_LAUNCHER_DIR")
    monkeypatch.setattr(runtime_cli, "_STARTUP_HEALERS", ())
    assert runtime_cli.main(["heal-launch-entries", "   "]) == 0
    assert "QUILL_LAUNCHER_DIR" not in os.environ

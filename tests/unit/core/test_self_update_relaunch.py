"""The restart half of "Install and restart now".

The update always applied. The app stopped coming back on 2026-08-17, when the
shared runtime landed and ``sys.executable`` stopped being the app's own frozen
exe: for an installed QuillVille app it is now ``QuillVilleRuntime.exe``, and in
a portable bundle it is a genuine ``pythonw.exe``. The helper relaunched it with
no arguments. The runtime then writes a usage line to stderr and exits 2 -- and
it is a windowed build, so nothing appeared at all; bare ``pythonw.exe`` opens an
interpreter with no script. Every symptom pointed at an update that had failed,
and the update had in fact installed perfectly.

Nothing here needs Windows: the script is a pure string and the resolver is a
pure function of ``sys.executable``'s name and ``__main__``'s spec.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import quill.core.self_update as su

RUNTIME_EXE = Path("C:/Users/me/AppData/Local/QuillVille/Runtime/3/QuillVilleRuntime.exe")
PORTABLE_PYTHONW = Path("C:/QuillLite/pythonw.exe")
APP_EXE = Path("C:/Apps/QuillRadio/QuillRadio.exe")


def _start_line(script: str) -> str:
    return next(line for line in script.splitlines() if line.startswith("start "))


def test_the_relaunch_names_the_module_when_the_runtime_is_the_executable() -> None:
    script = su.build_apply_update_script(
        pid=7,
        mode="installer",
        install_dir=RUNTIME_EXE.parent,
        exe_path=RUNTIME_EXE,
        log_path=Path("C:/log/apply-update.log"),
        setup_exe=Path("C:/dl/QuillLite-Setup-Shared-1.1.0.exe"),
        relaunch_args=["-m", "quill.apps.lite"],
    )
    assert _start_line(script).endswith("-m quill.apps.lite")


def test_the_module_reaches_the_apply_log_too() -> None:
    """The log is the only evidence a user can send when a restart goes wrong."""
    script = su.build_apply_update_script(
        pid=7,
        mode="portable",
        install_dir=PORTABLE_PYTHONW.parent,
        exe_path=PORTABLE_PYTHONW,
        log_path=Path("C:/log/apply-update.log"),
        source_dir=Path("C:/staging/app"),
        relaunch_args=["-m", "quill.apps.lite"],
    )
    relaunching = next(line for line in script.splitlines() if "relaunching" in line)
    assert "-m quill.apps.lite" in relaunching


def test_an_app_exe_is_still_relaunched_bare() -> None:
    """QUILL's own quill.exe must not be handed an argument -- it would read it
    as a file to open."""
    script = su.build_apply_update_script(
        pid=7,
        mode="installer",
        install_dir=APP_EXE.parent,
        exe_path=APP_EXE,
        log_path=Path("C:/log/apply-update.log"),
        setup_exe=Path("C:/dl/Setup.exe"),
    )
    assert _start_line(script) == 'start "" "C:\\Apps\\QuillRadio\\QuillRadio.exe"'


def test_the_runtime_and_a_portable_interpreter_both_get_the_module(monkeypatch) -> None:
    monkeypatch.setattr(su, "main_module", lambda: "quill.apps.lite")
    assert su.relaunch_command(RUNTIME_EXE) == ["-m", "quill.apps.lite"]
    assert su.relaunch_command(PORTABLE_PYTHONW) == ["-m", "quill.apps.lite"]


def test_an_apps_own_exe_gets_nothing(monkeypatch) -> None:
    monkeypatch.setattr(su, "main_module", lambda: "quill.apps.radio")
    assert su.relaunch_command(APP_EXE) == []


def test_no_module_means_no_arguments(monkeypatch) -> None:
    """A build whose __main__ carries no spec relaunches bare rather than
    inventing a module name to pass."""
    monkeypatch.setattr(su, "main_module", lambda: "")
    assert su.relaunch_command(RUNTIME_EXE) == []


def test_main_module_trims_a_package_entry_point(monkeypatch) -> None:
    fake = types.SimpleNamespace(__spec__=types.SimpleNamespace(name="quill.__main__"))
    monkeypatch.setitem(sys.modules, "__main__", fake)
    assert su.main_module() == "quill"


def test_main_module_keeps_a_plain_module_name(monkeypatch) -> None:
    """``QuillVilleRuntime.exe -m quill.apps.lite`` runs a module, not a
    package, and runpy reports it under exactly that name."""
    fake = types.SimpleNamespace(__spec__=types.SimpleNamespace(name="quill.apps.lite"))
    monkeypatch.setitem(sys.modules, "__main__", fake)
    assert su.main_module() == "quill.apps.lite"


def test_main_module_survives_a_missing_spec(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "__main__", types.SimpleNamespace())
    assert su.main_module() == ""


def test_begin_self_update_passes_the_relaunch_through(tmp_path, monkeypatch) -> None:
    """End to end: the argv the resolver computes is what lands in the script."""
    written: dict[str, str] = {}
    monkeypatch.setattr(su, "install_root_and_exe", lambda: (RUNTIME_EXE.parent, RUNTIME_EXE))
    monkeypatch.setattr(su, "main_module", lambda: "quill.apps.lite")
    monkeypatch.setattr(
        su, "write_and_launch_helper", lambda text, _dir: written.setdefault("script", text)
    )
    su.begin_self_update(
        download_path=tmp_path / "QuillLite-Setup-Shared-1.1.0.exe",
        portable=False,
        app_data_dir=tmp_path,
        pid=4242,
    )
    assert _start_line(written["script"]).endswith("-m quill.apps.lite")

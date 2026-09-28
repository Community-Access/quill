"""The shared runtime's entry point survives a windowed (console-less) launch.

A listener's fresh Quill Radio install showed PyInstaller's "Unhandled
exception in script" box -- "'NoneType' object has no attribute 'write'" --
because a windowed process has sys.stdout/sys.stderr set to None (2026-09-27).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest  # type: ignore[import-not-found]

_LAUNCHER = Path(__file__).resolve().parents[3] / "standalone" / "runtime" / "runtime_launcher.py"


def _load():
    spec = importlib.util.spec_from_file_location("quill_runtime_launcher_test", _LAUNCHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def windowed(monkeypatch):
    launcher = _load()
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    told: list[str] = []
    monkeypatch.setattr(launcher, "_tell", lambda text, title="": told.append(text))
    # Never give the test process a real taskbar identity.
    from quill.core import runtime_apps

    monkeypatch.setattr(runtime_apps, "claim_taskbar_identity", lambda _module: False)
    return launcher, told


def _installed(monkeypatch, *refs: str) -> None:
    from quill.core import runtime_apps

    apps = [app for app in runtime_apps.RUNTIME_APPS if app.ref_id in refs]
    monkeypatch.setattr(runtime_apps, "installed_apps", lambda _data_dir: apps)


def test_no_module_is_explained_not_a_traceback(windowed, monkeypatch) -> None:
    launcher, told = windowed
    _installed(monkeypatch)  # nothing registered: nothing to start
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe"])

    assert launcher.main() == 2
    assert told and "not an app of its own" in told[0]
    assert sys.stderr is not None and sys.stdout is not None


def test_a_module_that_writes_to_stderr_runs(windowed, monkeypatch) -> None:
    launcher, told = windowed
    ran: list[str] = []

    def _run(module, **_kwargs):
        sys.stderr.write("noise a windowed app used to die on\n")
        sys.stdout.write("more noise\n")
        ran.append(module)

    monkeypatch.setattr(launcher.runpy, "run_module", _run)
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "-m", "quill.apps.radio"])

    assert launcher.main() == 0
    assert ran == ["quill.apps.radio"] and told == []


def test_a_relaunch_without_dash_m_still_starts_the_app(windowed, monkeypatch) -> None:
    launcher, _told = windowed
    ran: list[str] = []
    monkeypatch.setattr(launcher.runpy, "run_module", lambda module, **_k: ran.append(module))
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "quill.apps.radio", "--safe-mode"])

    assert launcher.main() == 0
    assert ran == ["quill.apps.radio"]
    assert sys.argv == ["quill.apps.radio", "--safe-mode"]


def test_a_crash_is_saved_and_explained(windowed, monkeypatch, tmp_path) -> None:
    launcher, told = windowed
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    def _boom(module, **_kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(launcher.runpy, "run_module", _boom)
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "-m", "quill.apps.radio"])

    assert launcher.main() == 1
    reports = list((tmp_path / "QuillVille" / "Runtime" / "crash-reports").glob("crash-*.txt"))
    assert len(reports) == 1 and "kaboom" in reports[0].read_text(encoding="utf-8")
    assert told and "support@community-access.org" in told[0]


def test_a_launch_without_the_app_launcher_still_knows_its_root(
    windowed, monkeypatch, tmp_path
) -> None:
    # A taskbar pin targets QuillVilleRuntime.exe directly: nothing exported
    # QUILL_APP_ROOT, so libmpv beside the runtime was missed (2026-09-27).
    launcher, _told = windowed
    seen: list[str] = []
    monkeypatch.setattr(
        launcher.runpy,
        "run_module",
        lambda module, **_k: seen.append(launcher.os.environ.get("QUILL_APP_ROOT", "")),
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "QuillVilleRuntime.exe"))
    monkeypatch.setenv("QUILL_APP_ROOT", "placeholder")
    monkeypatch.delenv("QUILL_APP_ROOT")
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "-m", "quill.apps.radio"])

    assert launcher.main() == 0
    assert seen == [str(tmp_path)]


def test_the_launcher_s_app_root_is_kept(windowed, monkeypatch, tmp_path) -> None:
    launcher, _told = windowed
    monkeypatch.setattr(launcher.runpy, "run_module", lambda module, **_k: None)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "from-launcher"))
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "-m", "quill.apps.radio"])

    assert launcher.main() == 0
    assert launcher.os.environ["QUILL_APP_ROOT"] == str(tmp_path / "from-launcher")


# -- a bare launch: a taskbar pin Windows made from the running process -------
#
# Reported 2026-09-27: a listener pressed their pinned Quill Radio and heard
# "QuillVilleRuntime.exe is the shared engine ... it is not an app" instead of
# the radio. Windows pins the process it sees -- the runtime, with no arguments.


def test_a_bare_launch_with_one_app_installed_starts_that_app(windowed, monkeypatch) -> None:
    launcher, told = windowed
    _installed(monkeypatch, "radio")
    ran: list[str] = []
    monkeypatch.setattr(launcher.runpy, "run_module", lambda module, **_k: ran.append(module))
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe"])

    assert launcher.main() == 0
    assert ran == ["quill.apps.radio"] and told == []


def test_a_bare_launch_with_several_apps_asks_which(windowed, monkeypatch) -> None:
    launcher, told = windowed
    _installed(monkeypatch, "radio", "quilllite")
    offered: list[list[str]] = []

    def _pick(names):
        offered.append(names)
        return names.index("QUILL Lite")

    monkeypatch.setattr(launcher, "_pick", _pick)
    ran: list[str] = []
    monkeypatch.setattr(launcher.runpy, "run_module", lambda module, **_k: ran.append(module))
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe"])

    assert launcher.main() == 0
    assert offered == [["Quill Radio", "QUILL Lite"]]
    assert ran == ["quill.apps.lite"] and told == []


def test_cancelling_the_choice_starts_nothing(windowed, monkeypatch) -> None:
    launcher, _told = windowed
    _installed(monkeypatch, "radio", "weather")
    monkeypatch.setattr(launcher, "_pick", lambda _names: -1)
    ran: list[str] = []
    monkeypatch.setattr(launcher.runpy, "run_module", lambda module, **_k: ran.append(module))
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe"])

    assert launcher.main() == 2
    assert ran == []


def test_the_app_claims_its_taskbar_identity_before_it_runs(windowed, monkeypatch) -> None:
    launcher, _told = windowed
    from quill.core import runtime_apps

    order: list[str] = []
    monkeypatch.setattr(runtime_apps, "claim_taskbar_identity", lambda m: order.append(f"id:{m}"))
    monkeypatch.setattr(launcher.runpy, "run_module", lambda module, **_k: order.append("run"))
    monkeypatch.setattr(sys, "argv", ["QuillVilleRuntime.exe", "-m", "quill.apps.radio"])

    assert launcher.main() == 0
    assert order == ["id:quill.apps.radio", "run"]

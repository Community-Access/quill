"""Stale launch entries written by older shared-runtime builds get repaired.

2026-09-27: "start with Windows", the weather background check and the
recording wake were all written as the bare ``QuillVilleRuntime.exe``, which is
not an app. The app now rewrites its own entry at launch -- only one that
exists and is enabled, never from a portable copy or a dev run, never raising.
Nothing here touches the real registry or Task Scheduler.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from quill.core import paths
from quill.platform.windows import (
    launch_heal,
    radio_startup,
    recording_wake_task,
    scheduled_task,
    weather_startup,
)

RUNTIME = r"C:\Users\x\AppData\Local\QuillVille\Runtime\3.13\QuillVilleRuntime.exe"


class _Key:
    def __enter__(self) -> _Key:
        return self

    def __exit__(self, *_a: object) -> None:
        return None


class _Winreg:
    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self, store: dict[str, str] | None = None, *, locked: bool = False) -> None:
        self.store = dict(store or {})
        self.locked = locked
        self.writes: list[tuple[str, str]] = []

    def OpenKey(self, _hive: object, _path: str, *args: object) -> _Key:  # noqa: N802
        if self.locked and len(args) >= 2:
            raise PermissionError("policy")
        return _Key()

    def QueryValueEx(self, _key: object, name: str) -> tuple[str, int]:  # noqa: N802
        if name not in self.store:
            raise FileNotFoundError(name)
        return self.store[name], self.REG_SZ

    def SetValueEx(self, _key: object, name: str, _r: int, _t: int, value: str) -> None:  # noqa: N802
        self.writes.append((name, value))
        self.store[name] = value


@pytest.fixture
def launcher(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """This run came from an installed native launcher on the shared runtime."""
    for name in ("QuillRadio.exe", "QuillWeather.exe"):
        (tmp_path / name).write_bytes(b"MZ")
    monkeypatch.setattr(sys, "executable", RUNTIME)
    monkeypatch.setenv("QUILL_LAUNCHER_DIR", str(tmp_path))
    monkeypatch.setattr(paths, "portable_bundle_root", lambda: None)
    return tmp_path


def _radio_registry(monkeypatch: pytest.MonkeyPatch, store: dict[str, str]) -> _Winreg:
    fake = _Winreg(store)
    monkeypatch.setattr(radio_startup, "winreg", fake)
    monkeypatch.setattr(radio_startup, "is_windows", lambda: True)
    return fake


# -- the Run key -----------------------------------------------------------------


def test_the_broken_run_entry_is_rewritten_to_the_launcher(monkeypatch, launcher) -> None:
    fake = _radio_registry(monkeypatch, {"QuillRadio": f'"{RUNTIME}"'})
    assert radio_startup.heal_launch_at_startup(frozen=True) is True
    assert fake.store["QuillRadio"] == f'"{launcher / "QuillRadio.exe"}"'


def test_no_entry_means_none_is_created(monkeypatch, launcher) -> None:
    fake = _radio_registry(monkeypatch, {})
    assert radio_startup.heal_launch_at_startup(frozen=True) is False
    assert fake.writes == []


def test_a_current_entry_is_not_rewritten(monkeypatch, launcher) -> None:
    fake = _radio_registry(monkeypatch, {"QuillRadio": f'"{launcher / "QuillRadio.exe"}"'})
    assert radio_startup.heal_launch_at_startup(frozen=True) is False
    assert fake.writes == []


def test_a_portable_copy_never_heals(monkeypatch, launcher, tmp_path) -> None:
    fake = _radio_registry(monkeypatch, {"QuillRadio": f'"{RUNTIME}"'})
    monkeypatch.setattr(paths, "portable_bundle_root", lambda: tmp_path)
    assert radio_startup.heal_launch_at_startup(frozen=True) is False
    assert fake.writes == []


def test_a_dev_run_never_heals(monkeypatch, launcher) -> None:
    fake = _radio_registry(monkeypatch, {"QuillRadio": f'"{RUNTIME}"'})
    assert radio_startup.heal_launch_at_startup(frozen=False) is False
    assert fake.writes == []


def test_a_locked_registry_costs_the_heal_not_the_launch() -> None:
    fake = _Winreg({"QuillRadio": f'"{RUNTIME}"'}, locked=True)
    assert launch_heal.heal_run_value(fake, "QuillRadio", '"x.exe"') is False
    assert launch_heal.heal_run_value(None, "QuillRadio", '"x.exe"') is False


def test_the_weather_entry_keeps_its_tray_flag(monkeypatch, launcher) -> None:
    fake = _Winreg({"QuillWeather": f'"{RUNTIME}" --tray'})
    monkeypatch.setattr(weather_startup, "winreg", fake)
    monkeypatch.setattr(weather_startup, "is_windows", lambda: True)
    assert weather_startup.heal_launch_at_startup(frozen=True) is True
    assert fake.store["QuillWeather"] == f'"{launcher / "QuillWeather.exe"}" --tray'


# -- scheduled tasks ---------------------------------------------------------------


def _task(command: str, arguments: str = "", *, extra: str = "", enabled: str = "true") -> str:
    args = f"<Arguments>{arguments}</Arguments>" if arguments else ""
    return (
        f"<Task><Triggers><TimeTrigger>{extra}<Enabled>true</Enabled></TimeTrigger></Triggers>"
        f"<Settings><Enabled>{enabled}</Enabled></Settings>"
        f"<Actions><Exec><Command>{command}</Command>{args}</Exec></Actions></Task>"
    )


def test_the_weather_check_is_reregistered_at_its_own_cadence(monkeypatch, launcher) -> None:
    calls: list[int] = []
    monkeypatch.setattr(scheduled_task, "is_windows", lambda: True)
    monkeypatch.setattr(scheduled_task, "register", lambda m: calls.append(m) or True)
    xml = _task(
        RUNTIME, "--check-once", extra="<Repetition><Interval>PT1H30M</Interval></Repetition>"
    )
    assert scheduled_task.heal_registered_task(frozen=True, query=lambda: xml) is True
    assert calls == [90]


def test_a_disabled_or_absent_weather_check_is_left_alone(monkeypatch, launcher) -> None:
    calls: list[int] = []
    monkeypatch.setattr(scheduled_task, "is_windows", lambda: True)
    monkeypatch.setattr(scheduled_task, "register", lambda m: calls.append(m) or True)
    xml = _task(RUNTIME, "--check-once", enabled="false")
    assert scheduled_task.heal_registered_task(frozen=True, query=lambda: xml) is False
    assert scheduled_task.heal_registered_task(frozen=True, query=lambda: "") is False
    assert calls == []


def _wake(monkeypatch: pytest.MonkeyPatch) -> list[tuple[datetime, str]]:
    calls: list[tuple[datetime, str]] = []
    monkeypatch.setattr(recording_wake_task, "is_windows", lambda: True)
    monkeypatch.setattr(
        recording_wake_task,
        "register",
        lambda when, command="": calls.append((when, command)) or True,
    )
    return calls


def test_a_pending_wake_is_reregistered_for_the_same_moment(monkeypatch, launcher) -> None:
    calls = _wake(monkeypatch)
    now = datetime(2026, 9, 27, 12, 0)
    xml = _task(RUNTIME, extra="<StartBoundary>2026-09-28T06:30:00</StartBoundary>")
    assert recording_wake_task.heal_registered_task(frozen=True, now=now, query=lambda: xml)
    assert calls == [(datetime(2026, 9, 28, 6, 30), f'"{launcher / "QuillRadio.exe"}"')]


def test_a_wake_already_past_is_not_rearmed(monkeypatch, launcher) -> None:
    calls = _wake(monkeypatch)
    now = datetime(2026, 9, 29)
    xml = _task(RUNTIME, extra="<StartBoundary>2026-09-28T06:30:00</StartBoundary>")
    assert not recording_wake_task.heal_registered_task(frozen=True, now=now, query=lambda: xml)
    assert calls == []


def test_a_current_wake_is_left_alone(monkeypatch, launcher) -> None:
    calls = _wake(monkeypatch)
    when = datetime.now() + timedelta(days=1)
    xml = _task(
        str(launcher / "QuillRadio.exe"),
        extra=f"<StartBoundary>{when:%Y-%m-%dT%H:%M:%S}</StartBoundary>",
    )
    assert not recording_wake_task.heal_registered_task(frozen=True, query=lambda: xml)
    assert calls == []


def test_the_wake_definition_splits_command_and_arguments() -> None:
    xml = recording_wake_task.task_xml(
        datetime(2026, 9, 28, 6, 30), f'"{RUNTIME}" -m quill.apps.radio'
    )
    assert f"<Command>{RUNTIME}</Command>" in xml
    assert "<Arguments>-m quill.apps.radio</Arguments>" in xml
    # And it reads back as the command it was written from.
    assert launch_heal.task_command(xml) == f'"{RUNTIME}" -m quill.apps.radio'


def test_heal_in_background_runs_every_healer_and_swallows_failures() -> None:
    ran: list[str] = []

    class _Tasks:
        def submit(self, _name: str, func: Any, **_kw: Any) -> None:
            func()

    def _boom() -> bool:
        raise RuntimeError("x")

    launch_heal.heal_in_background(_Tasks(), _boom, lambda: ran.append("ok") or True)
    launch_heal.heal_in_background(None, _boom)
    assert ran == ["ok"]

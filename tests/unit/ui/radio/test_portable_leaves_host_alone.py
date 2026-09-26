"""A portable Quill Radio changes nothing about the computer it visits.

Two things in Radio *configure the machine* rather than write a file: the
Task Scheduler entry that wakes the computer for a scheduled recording, and the
Run-key entry behind "Start Quill Radio with Windows". Either one, made from a
USB stick on a friend's computer, outlives the stick -- the wake task would
wake their computer to run a program from a drive letter that means something
else tomorrow. A portable copy does neither, says so, and keeps the session-only
keep-awake that needs no change to the machine.

Every check here goes through ``quill.core.paths.portable_bundle_root`` -- the
one shared answer -- so patching it is the whole of "running portable".
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import paths


@pytest.fixture
def portable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(paths, "portable_bundle_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "portable_bundle_root", lambda: None)


class _Task:
    """recording_wake_task, recording every call that would reach schtasks."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def is_windows(self) -> bool:
        return True

    def register(self, _when: Any) -> bool:
        self.calls.append("register")
        return True

    def unregister(self) -> bool:
        self.calls.append("unregister")
        return True


def _host() -> Any:
    history = SimpleNamespace(wake_for_scheduled_recording=True, keep_awake_before_recording=True)
    return SimpleNamespace(_radio_history=history, _radio_scheduler=None)


def _patch_task(monkeypatch: pytest.MonkeyPatch) -> _Task:
    from quill.platform.windows import recording_wake_task

    task = _Task()
    for name in ("is_windows", "register", "unregister"):
        monkeypatch.setattr(recording_wake_task, name, getattr(task, name))
    return task


def test_a_portable_copy_never_touches_task_scheduler(
    monkeypatch: pytest.MonkeyPatch, portable: Path
) -> None:
    from quill.ui.radio import schedule_wake_ui

    task = _patch_task(monkeypatch)
    schedule_wake_ui.refresh_wake_task(_host())
    # Not even the delete: every launch used to spawn schtasks to remove a task
    # that was never there.
    assert task.calls == []


def test_an_installed_copy_still_keeps_the_wake_task_in_step(
    monkeypatch: pytest.MonkeyPatch, installed: None
) -> None:
    from quill.ui.radio import schedule_wake_ui

    task = _patch_task(monkeypatch)
    schedule_wake_ui.refresh_wake_task(_host())
    assert task.calls == ["unregister"]  # nothing scheduled: leave nothing behind


def test_the_wake_preference_is_greyed_out_and_says_why_when_portable(portable: Path) -> None:
    from quill.apps import radio_preferences

    box = radio_preferences._wake_checkbox(True)
    assert box.enabled is False
    assert box.value is True  # an installed copy sharing the data is not switched off
    assert "does not change this computer's Task Scheduler" in box.help_text
    assert box.help_text == radio_preferences.PORTABLE_WAKE_HELP


def test_the_wake_preference_is_live_when_installed(installed: None) -> None:
    from quill.apps import radio_preferences

    box = radio_preferences._wake_checkbox(False)
    assert box.enabled is True
    assert "Task Scheduler" in box.help_text
    assert box.name == "Wa&ke the computer for a scheduled recording"


class _Registry:
    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self) -> None:
        self.opened = 0

    def OpenKey(self, *_args: Any) -> Any:  # noqa: N802 - winreg's name
        self.opened += 1
        raise OSError("not in a test")


def test_a_portable_copy_never_writes_the_run_key(
    monkeypatch: pytest.MonkeyPatch, portable: Path
) -> None:
    from quill.platform.windows import radio_startup

    registry = _Registry()
    monkeypatch.setattr(radio_startup, "winreg", registry)
    monkeypatch.setattr(radio_startup.sys, "platform", "win32")

    radio_startup.set_launch_at_startup(True)

    assert registry.opened == 0
    # An installed Quill Radio's entry on the same computer is not this copy's:
    # the menu shows it unchecked, so toggling cannot remove it.
    assert radio_startup.is_launch_at_startup_enabled() is False
    assert radio_startup.running_portable() is True
    assert "portable copy does not add itself" in radio_startup.PORTABLE_REFUSAL


def test_an_installed_copy_still_reaches_the_run_key(
    monkeypatch: pytest.MonkeyPatch, installed: None
) -> None:
    from quill.platform.windows import radio_startup

    registry = _Registry()
    monkeypatch.setattr(radio_startup, "winreg", registry)
    monkeypatch.setattr(radio_startup.sys, "platform", "win32")

    radio_startup.set_launch_at_startup(True)

    assert registry.opened == 1


def test_the_menu_toggle_announces_instead_of_writing(
    monkeypatch: pytest.MonkeyPatch, portable: Path
) -> None:
    from quill.apps.radio import RadioAppFrame
    from quill.platform.windows import radio_startup

    monkeypatch.setattr(radio_startup, "is_windows", lambda: True)
    writes: list[bool] = []
    monkeypatch.setattr(radio_startup, "set_launch_at_startup", writes.append)
    said: list[str] = []
    host = SimpleNamespace(_announce=said.append)

    RadioAppFrame._toggle_launch_at_startup(host)  # type: ignore[arg-type]

    assert writes == []
    assert said == [radio_startup.PORTABLE_REFUSAL]

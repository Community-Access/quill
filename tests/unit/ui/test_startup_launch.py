"""The shared start-minimized pieces (quill/ui/startup_launch.py).

wx-free on purpose: the launch decision and QUILL's hidden first show are
plain logic over a frame's attributes, and the menu row's label is a string
the menu accelerator rule reads.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from quill.ui import startup_launch
from quill.ui.startup_launch import (
    START_MINIMIZED_LABEL,
    editor_starts_hidden,
    present_at_launch,
    starts_in_tray,
)


@pytest.mark.parametrize(
    ("argv", "saved", "expected"),
    [
        ([], False, False),
        ([], True, True),
        (["--tray"], False, True),
        (["--window"], True, False),  # a login launch that asked for the window
        (["--tray", "--window"], False, False),
    ],
)
def test_window_beats_tray_and_the_saved_option(argv, saved, expected) -> None:
    assert starts_in_tray(saved, argv) is expected


def test_the_menu_row_advertises_a_key_and_an_access_letter() -> None:
    label, _tab, key = START_MINIMIZED_LABEL.partition("\t")
    assert key == "Ctrl+Alt+L"
    assert "&" in label and not label.startswith("&M")


class _Frame:
    def __init__(self, shown: bool = False) -> None:
        self.shown = shown
        self.calls: list[str] = []

    def IsShown(self) -> bool:  # noqa: N802 - wx's name
        return self.shown

    def Hide(self) -> None:  # noqa: N802
        self.calls.append("hide")

    def Show(self) -> None:  # noqa: N802
        self.calls.append("show")

    def Raise(self) -> None:  # noqa: N802
        self.calls.append("raise")


def test_a_tray_launch_stays_hidden_and_says_where_it_went() -> None:
    said: list[str] = []
    host = SimpleNamespace(frame=_Frame(), _set_status=said.append)
    assert present_at_launch(host, "Quill Radio", in_tray=True) is False
    assert host.frame.calls == ["hide"]
    assert said == ["Quill Radio started minimized to the system tray."]


def test_a_window_already_showing_goes_to_the_tray_the_apps_own_way() -> None:
    sent: list[bool] = []
    host = SimpleNamespace(frame=_Frame(shown=True), _set_status=None)
    present_at_launch(host, "Quill Inkwell", in_tray=True, to_tray=lambda: sent.append(True))
    assert sent == [True] and host.frame.calls == []


def test_an_ordinary_launch_shows_and_raises() -> None:
    host = SimpleNamespace(frame=_Frame(), _set_status=None)
    assert present_at_launch(host, "QUILL Cast", in_tray=False, raise_window=False) is True
    assert host.frame.calls == ["show"]


def _editor(*, tray_enabled: bool, icon: object) -> SimpleNamespace:
    status: list[str] = []
    queued: list[object] = []
    editor = SimpleNamespace(
        settings=SimpleNamespace(tray_enabled=tray_enabled),
        _tray_icon=None,
        frame=_Frame(),
        starting_up=True,
        _startup_deferred_ran=False,
        _run_deferred_startup_tasks=object(),
        _wx=SimpleNamespace(CallAfter=queued.append),
        _set_status=status.append,
        status=status,
        queued=queued,
    )
    editor._ensure_tray_icon = lambda: setattr(editor, "_tray_icon", icon)
    return editor


def test_quill_hides_only_when_its_tray_icon_really_exists(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    no_icon = _editor(tray_enabled=True, icon=None)
    assert editor_starts_hidden(no_icon, True) is False
    assert no_icon.frame.calls == [] and no_icon.starting_up is True

    hidden = _editor(tray_enabled=True, icon=object())
    assert editor_starts_hidden(hidden, True) is True
    assert hidden.frame.calls == ["hide"]
    assert hidden.starting_up is False
    assert hidden.queued == [hidden._run_deferred_startup_tasks]


def test_quill_shows_normally_without_the_flag_or_the_tray(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert editor_starts_hidden(_editor(tray_enabled=True, icon=object()), False) is False
    assert editor_starts_hidden(_editor(tray_enabled=False, icon=object()), True) is False


def test_settings_apply_writes_the_choice_and_the_run_key(monkeypatch) -> None:
    from quill.platform.windows import startup, startup_options

    calls: list[tuple] = []
    monkeypatch.setattr(
        startup_options, "set_start_minimized", lambda app, on: calls.append(("choice", app, on))
    )
    monkeypatch.setattr(
        startup,
        "set_launch_at_startup",
        lambda on, *, start_minimized: calls.append(("run", on, start_minimized)),
    )
    settings = SimpleNamespace(
        launch_at_windows_startup=True, start_minimized_at_windows_startup=True
    )
    startup_launch.apply_editor_startup(settings)
    assert calls == [("choice", "quill", True), ("run", True, True)]

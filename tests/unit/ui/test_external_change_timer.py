"""The shared wx half of the external-change watcher, with real wx (2026-10-04).

The clock both editors poll on, the question with QUILL Lite's Save As answer,
and QUILL Lite's Preferences group for the four settings.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.ui.external_change_timer import ExternalChangeTimer, modal_window_open


@pytest.fixture
def application() -> Any:
    existing = wx.GetApp()
    app = existing or wx.App(False)
    yield app
    if existing is None:
        app.Destroy()


@pytest.fixture
def frame(application: Any) -> Any:
    window = wx.Frame(None, title="Watched")
    yield window
    window.Destroy()


def _find(dialog: Any, kind: type, label: str) -> Any:
    for child in dialog.GetChildren():
        if isinstance(child, kind) and child.GetLabel().replace("&", "") == label:
            return child
    raise AssertionError(f"no {kind.__name__} labelled {label!r}")


@pytest.mark.machine_global
def test_a_tick_polls_once_and_pauses_while_busy_or_under_a_modal(frame: Any) -> None:
    ticks: list[int] = []
    busy = {"now": False}
    timer = ExternalChangeTimer(
        frame, lambda: ticks.append(1), interval=lambda: 500, busy=lambda: busy["now"]
    )
    timer.start()
    try:
        assert timer.running
        timer.tick()
        assert ticks == [1]

        busy["now"] = True
        timer.tick()
        assert ticks == [1]
        busy["now"] = False

        # What ShowModal and a message box both do to the window underneath.
        frame.Disable()
        assert modal_window_open(frame)
        timer.tick()
        assert ticks == [1]
        frame.Enable()
        timer.tick()
        assert ticks == [1, 1]
    finally:
        timer.stop()
    assert not timer.running


@pytest.mark.machine_global
def test_a_tick_never_re_enters_itself(frame: Any) -> None:
    depth: list[int] = []
    timer: ExternalChangeTimer

    def on_tick() -> None:
        depth.append(1)
        timer.tick()  # the question's own modal loop letting the timer fire

    timer = ExternalChangeTimer(frame, on_tick, interval=lambda: 500)
    timer.tick()
    assert depth == [1]


@pytest.mark.machine_global
def test_quill_lites_question_offers_save_as_with_keep_mine_on_enter(
    application: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import external_change_dialog as module
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()  # SetHelpText stores nothing without one
    seen: dict[str, Any] = {}

    def show(dialog: Any, _label: str) -> int:
        seen["save_as"] = _find(dialog, wx.Button, "Save As...")
        keep = _find(dialog, wx.Button, "Keep Mine")
        seen["keep_default"] = keep.IsDefault() if hasattr(keep, "IsDefault") else None
        seen["help"] = _find(dialog, wx.CheckBox, "Do not ask me again for .md files").GetHelpText()
        return wx.ID_APPLY

    monkeypatch.setattr(module, "show_modal_dialog", show)
    answer = module.ask_external_change(
        None,
        "plan.md",
        buffer_dirty=True,
        alternative=module.SAVE_AS,
        default_keep=True,
        forget_hint="Preferences undoes this.",
    )
    assert answer.action == module.SAVE_AS
    assert answer.remembered_value == ""  # a one-off, never a policy
    assert seen["keep_default"] in (True, None)
    assert seen["help"].endswith("Preferences undoes this.")


@pytest.mark.machine_global
def test_quills_question_is_unchanged(application: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui import external_change_dialog as module

    def show(dialog: Any, _label: str) -> int:
        _find(dialog, wx.Button, "Open Disk Version in a New Tab")
        return wx.ID_APPLY

    monkeypatch.setattr(module, "show_modal_dialog", show)
    answer = module.ask_external_change(None, "plan.md", buffer_dirty=False)
    assert answer.action == module.NEW_TAB


@pytest.mark.machine_global
def test_lite_preferences_carry_the_four_settings_and_the_way_back(
    application: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps import lite_preferences
    from quill.core.lite.settings import Settings
    from quill.ui.app_context_help import ensure_help_provider
    from quill.ui.preferences_search import install_preferences_search

    ensure_help_provider()
    settings = Settings()
    settings.external_change_always_keep = [".docx"]
    spoken: list[str] = []
    found: list[str] = []

    def answer_ok(dialog: Any, _label: str) -> int:
        search = install_preferences_search(dialog)
        search.search.SetValue("external changes")
        search._on_search(None)
        found.extend(target.label for target in search.matches)
        search.close()
        watch = _find(dialog, wx.CheckBox, "Watch the open file for external changes")
        assert watch.GetHelpText()
        _find(dialog, wx.CheckBox, "Reload automatically when you have no unsaved edits").SetValue(
            True
        )
        _find(dialog, wx.CheckBox, "Ask before discarding unsaved edits on a conflict")
        _find(dialog, wx.StaticText, "External-change debounce (milliseconds):")
        forget = _find(dialog, wx.Button, "Forget remembered file-change answers")
        forget.Command(wx.CommandEvent(wx.wxEVT_BUTTON, forget.GetId()))
        return wx.ID_OK

    monkeypatch.setattr(lite_preferences, "show_modal_dialog", answer_ok)
    result = lite_preferences.edit_preferences(None, settings, announce=spoken.append)
    application.Yield()

    assert "Watch the open file for external changes" in found
    assert result.changed
    assert settings.external_change_auto_reload_when_clean is True
    assert settings.external_change_always_keep == []
    assert spoken == ["1 remembered file-format answer will be forgotten when you press OK."]

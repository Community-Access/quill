"""Headless build smoke for the Audio Studio Sleep Timer dialog (Phase 2)."""

from __future__ import annotations

import pytest
import wx

from quill.core.audio_studio.sleep_timer import SleepTimerSetting
from quill.ui.audio_studio.sleep_timer_dialog import SleepTimerDialog


@pytest.fixture
def app():
    import wx

    a = wx.App(False)
    yield a
    a.Destroy()


def test_dialog_builds(app) -> None:
    dlg = SleepTimerDialog(None, SleepTimerSetting(enabled=True, delay_minutes=30.0))
    assert dlg is not None
    dlg.Destroy()


def test_dialog_value_round_trips(app) -> None:
    dlg = SleepTimerDialog(
        None, SleepTimerSetting(enabled=True, delay_minutes=45.0, end_of_chapter=True)
    )
    value = dlg.value()
    assert value.enabled is True
    assert value.delay_minutes == 45.0
    assert value.end_of_chapter is True
    dlg.Destroy()


def test_dialog_disable_toggle_reflected(app) -> None:
    dlg = SleepTimerDialog(None, SleepTimerSetting(enabled=False, delay_minutes=20.0))
    assert dlg.value().enabled is False
    dlg.Destroy()


def test_dialog_focusable_controls_have_names(app) -> None:
    """Every focusable control exposes an accessible name (GATE-A11Y)."""
    dlg = SleepTimerDialog(None, SleepTimerSetting(enabled=True, delay_minutes=30.0))
    try:
        # CheckBoxes and buttons carry their label as the accessible name;
        # the SpinCtrl was given an explicit Name.
        assert dlg._enabled.GetLabel()
        assert dlg._end_of_chapter.GetLabel()
        assert dlg._minutes.GetName() == "Sleep timer delay in minutes"
        for btn_id in (wx.ID_OK, wx.ID_CANCEL):
            btn = dlg.FindWindowById(btn_id)
            assert btn is not None and btn.GetLabel()
    finally:
        dlg.Destroy()
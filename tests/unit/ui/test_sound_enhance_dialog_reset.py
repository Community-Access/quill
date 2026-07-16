"""SoundEnhanceDialog's optional "Reset to Default" button.

Only Radio's per-station Sound Enhancements can be reset (clearing a
favorite's override so it goes back to following the shared default);
Podcasts' call site doesn't pass ``on_reset``, so this button must not
appear there. Callback-based so the dialog itself stays ignorant of
favorites/overrides -- the caller's callback does the real work.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.sound_enhance_dialog import SoundEnhanceDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _dialog(wx_app, **kwargs) -> SoundEnhanceDialog:
    frame = wx.Frame(None)
    dialog = SoundEnhanceDialog(
        frame,
        bass_db=0.0,
        mid_db=0.0,
        treble_db=0.0,
        compressor_enabled=False,
        **kwargs,
    )
    return dialog


def test_no_reset_button_without_on_reset(wx_app) -> None:
    dialog = _dialog(wx_app)
    assert dialog._reset_btn is None
    dialog.dialog.Destroy()


def test_reset_button_present_when_on_reset_given(wx_app) -> None:
    dialog = _dialog(wx_app, on_reset=lambda: None)
    assert dialog._reset_btn is not None
    assert "Reset" in dialog._reset_btn.GetLabel()
    dialog.dialog.Destroy()


def test_clicking_reset_button_calls_callback_exactly_once(wx_app) -> None:
    calls: list[bool] = []
    dialog = _dialog(wx_app, on_reset=lambda: calls.append(True))

    btn = dialog._reset_btn
    assert btn is not None
    btn.Command(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId()))

    assert calls == [True]
    dialog.dialog.Destroy()

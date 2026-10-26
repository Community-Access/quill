"""Up is louder on Quill Radio's real volume slider, pressed as a real key.

Reported 2026-10-26 on 3.2.0 build 4 ("the keys are reversed for volume"). The
slider fix (``slider_keys.bind_up_means_more``) was only ever tested with a
stand-in event; this sends a real ``WM_KEYDOWN`` to the real slider in the real
Radio window, so anything that claims the key first -- a frame char hook, an
accelerator -- is in the path too.
"""

from __future__ import annotations

import sys

import pytest

from tests.wx_session import shared_wx_app

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="Win32 key messages"),
    pytest.mark.machine_global,
]

wx = pytest.importorskip("wx")

_WM_KEYDOWN, _WM_KEYUP = 0x0100, 0x0101
_VK = {"Up": 0x26, "Down": 0x28, "PageUp": 0x21, "PageDown": 0x22}


def _press(slider: object, key: str) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    vk = _VK[key]
    scan = user32.MapVirtualKeyW(vk, 0)
    flags = 1 | (scan << 16) | (1 << 24)
    handle = slider.GetHandle()  # type: ignore[attr-defined]
    user32.SendMessageW(handle, _WM_KEYDOWN, vk, flags)
    user32.SendMessageW(handle, _WM_KEYUP, vk, flags | (3 << 30))
    wx.Yield()


@pytest.fixture
def radio_frame(quill_data_dir, monkeypatch):
    shared_wx_app()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.radio import first_run_dialog

    # A fresh profile is greeted by a modal welcome; this test is about the keys.
    monkeypatch.setattr(first_run_dialog, "maybe_run_first_run", lambda _host: False)

    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    frame.frame.Show()
    yield frame
    # Close the way the app closes (test_menu_accelerators.py): only its
    # shutdown stops its timers, and it installs a process-wide dialog policy.
    frame._radio_shutdown()
    set_transition_announcement_policy(None)


def test_up_is_louder_on_the_real_slider(radio_frame) -> None:
    slider = radio_frame._volume_slider
    slider.SetValue(50)
    slider.SetFocus()
    wx.Yield()
    steps = []
    for key in ("Up", "Up", "Down", "PageUp", "PageDown"):
        before = slider.GetValue()
        _press(slider, key)
        steps.append((key, slider.GetValue() - before))
    line, page = slider.GetLineSize(), slider.GetPageSize()
    assert steps == [
        ("Up", line),
        ("Up", line),
        ("Down", -line),
        ("PageUp", page),
        ("PageDown", -page),
    ]

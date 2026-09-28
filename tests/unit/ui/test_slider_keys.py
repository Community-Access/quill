"""Up means more on a horizontal slider (``quill/ui/slider_keys.py``).

A Windows trackbar answers Up with less and Down with more. A Quill Radio
listener reported the volume slider as backwards (2026-09-28); the helper
flips the four vertical keys and fires ``EVT_SLIDER`` so the app hears it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import wx

from quill.ui.slider_keys import bind_up_means_more, step_for_key


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (wx.WXK_UP, +1),
        (wx.WXK_NUMPAD_UP, +1),
        (wx.WXK_DOWN, -1),
        (wx.WXK_NUMPAD_DOWN, -1),
        (wx.WXK_PAGEUP, +10),
        (wx.WXK_NUMPAD_PAGEUP, +10),
        (wx.WXK_PAGEDOWN, -10),
        (wx.WXK_NUMPAD_PAGEDOWN, -10),
    ],
)
def test_up_and_page_up_are_more_down_and_page_down_are_less(key: int, expected: int) -> None:
    assert step_for_key(key, line_size=1, page_size=10) == expected


@pytest.mark.parametrize("key", [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_HOME, wx.WXK_END, ord("A")])
def test_every_other_key_is_left_to_the_trackbar(key: int) -> None:
    assert step_for_key(key, line_size=1, page_size=10) is None


def test_a_zero_step_still_moves() -> None:
    assert step_for_key(wx.WXK_UP, line_size=0, page_size=0) == 1


@dataclass
class _Key:
    code: int
    ctrl: bool = False
    shift: bool = False
    alt: bool = False
    skipped: list[bool] = field(default_factory=list)

    def GetKeyCode(self) -> int:  # noqa: N802 - wx naming
        return self.code

    def ControlDown(self) -> bool:  # noqa: N802
        return self.ctrl

    def ShiftDown(self) -> bool:  # noqa: N802
        return self.shift

    def AltDown(self) -> bool:  # noqa: N802
        return self.alt

    def Skip(self, skip: bool = True) -> None:  # noqa: N802
        self.skipped.append(skip)


def _slider_with_handler() -> tuple[wx.Frame, wx.Slider, list[int]]:
    frame = wx.Frame(None)
    slider = wx.Slider(frame, value=50, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL)
    heard: list[int] = []
    slider.Bind(wx.EVT_SLIDER, lambda e: heard.append(slider.GetValue()))
    bind_up_means_more(slider)
    return frame, slider, heard


def _press(slider: wx.Slider, key: _Key) -> None:
    """Drive the helper's EVT_KEY_DOWN handler with a stand-in event.

    A real keystroke needs focus, and focus needs a screen; the handler is
    what the helper bound, reached the way it exposes it for exactly this.
    """
    slider._quill_up_means_more(key)


def test_up_raises_the_volume_and_the_app_hears_it(wx_app: wx.App) -> None:
    frame, slider, heard = _slider_with_handler()
    try:
        _press(slider, _Key(wx.WXK_UP))
        assert slider.GetValue() == 51
        _press(slider, _Key(wx.WXK_PAGEUP))
        assert slider.GetValue() == 51 + slider.GetPageSize()
        assert heard == [51, 51 + slider.GetPageSize()]
    finally:
        frame.Destroy()


def test_down_lowers_the_volume(wx_app: wx.App) -> None:
    frame, slider, heard = _slider_with_handler()
    try:
        _press(slider, _Key(wx.WXK_DOWN))
        _press(slider, _Key(wx.WXK_PAGEDOWN))
        assert slider.GetValue() == 49 - slider.GetPageSize()
        assert heard == [49, 49 - slider.GetPageSize()]
    finally:
        frame.Destroy()


def test_at_the_top_up_is_silent(wx_app: wx.App) -> None:
    frame, slider, heard = _slider_with_handler()
    try:
        slider.SetValue(100)
        key = _Key(wx.WXK_UP)
        _press(slider, key)
        assert slider.GetValue() == 100
        assert heard == []
        assert key.skipped == []  # consumed, not handed to the trackbar to lower it
    finally:
        frame.Destroy()


def test_chords_and_other_keys_pass_through(wx_app: wx.App) -> None:
    frame, slider, heard = _slider_with_handler()
    try:
        ctrl_up = _Key(wx.WXK_UP, ctrl=True)
        _press(slider, ctrl_up)
        right = _Key(wx.WXK_RIGHT)
        _press(slider, right)
        assert slider.GetValue() == 50
        assert heard == []
        assert ctrl_up.skipped == [True]
        assert right.skipped == [True]
    finally:
        frame.Destroy()


_QUILL = Path(__file__).resolve().parents[3] / "quill"


def test_every_horizontal_slider_in_the_family_binds_up_means_more() -> None:
    """The rule is family-wide (2026-09-28): a slider one app fixes and another
    leaves native is a worse bug than the one reported. A new ``wx.Slider``
    fails here until its module binds the helper (or the slider is vertical,
    where the trackbar's Up is already up)."""
    offenders: list[str] = []
    for path in sorted(_QUILL.rglob("*.py")):
        if path.name == "slider_keys.py":
            continue
        source = path.read_text(encoding="utf-8")
        horizontal = [
            m
            for m in re.finditer(r"wx\.Slider\(", source)
            if "SL_VERTICAL" not in source[m.start() : m.start() + 400]
        ]
        if horizontal and "bind_up_means_more(" not in source:
            offenders.append(str(path.relative_to(_QUILL.parent)))
    assert offenders == [], f"horizontal wx.Slider without bind_up_means_more: {offenders}"

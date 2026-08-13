"""Alt+F4 minimizes to the system tray (opt-in preference, Radio + Cast).

The char hook intercepts Alt+F4 before Windows turns it into a close, so
the window tucks away with playback running; with the preference off (the
default) the key flows through untouched and the normal close path --
including 'When closing the window' -- still applies.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import wx

from quill.apps.podcasts import PodcastsAppFrame
from quill.apps.radio import RadioAppFrame


class _FakeKeyEvent:
    def __init__(
        self, *, key_code: int, alt: bool, shift: bool = False, ctrl: bool = False
    ) -> None:
        self._key_code = key_code
        self._alt = alt
        self._shift = shift
        self._ctrl = ctrl
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._key_code

    def AltDown(self) -> bool:
        return self._alt

    def ShiftDown(self) -> bool:
        return self._shift

    def ControlDown(self) -> bool:
        return self._ctrl

    def Skip(self) -> None:
        self.skipped = True


def _radio_frame(*, alt_f4_to_tray: bool) -> Any:
    frame = RadioAppFrame.__new__(RadioAppFrame)
    frame._radio_history = SimpleNamespace(alt_f4_to_tray=alt_f4_to_tray)
    frame.tray_calls = []  # type: ignore[attr-defined]
    frame._send_to_tray = lambda: frame.tray_calls.append(True)
    return frame


def _cast_frame(*, alt_f4_to_tray: bool) -> Any:
    frame = PodcastsAppFrame.__new__(PodcastsAppFrame)
    frame._podcast_history = SimpleNamespace(alt_f4_to_tray=alt_f4_to_tray)
    frame.tray_calls = []  # type: ignore[attr-defined]
    frame._send_to_tray = lambda: frame.tray_calls.append(True)
    return frame


def test_radio_alt_f4_goes_to_tray_when_enabled() -> None:
    frame = _radio_frame(alt_f4_to_tray=True)
    event = _FakeKeyEvent(key_code=wx.WXK_F4, alt=True)
    RadioAppFrame._on_radio_char_hook(frame, event)
    assert frame.tray_calls == [True]
    assert event.skipped is False  # swallowed: no close event follows


def test_radio_alt_f4_flows_through_when_disabled() -> None:
    frame = _radio_frame(alt_f4_to_tray=False)
    event = _FakeKeyEvent(key_code=wx.WXK_F4, alt=True)
    RadioAppFrame._on_radio_char_hook(frame, event)
    assert frame.tray_calls == []
    assert event.skipped is True  # normal close path (close_action) applies


def test_radio_other_keys_always_flow_through() -> None:
    frame = _radio_frame(alt_f4_to_tray=True)
    for key_code, alt in ((wx.WXK_F4, False), (ord("Q"), True), (wx.WXK_ESCAPE, False)):
        event = _FakeKeyEvent(key_code=key_code, alt=alt)
        RadioAppFrame._on_radio_char_hook(frame, event)
        assert event.skipped is True
    assert frame.tray_calls == []


def test_cast_alt_f4_goes_to_tray_when_enabled() -> None:
    frame = _cast_frame(alt_f4_to_tray=True)
    event = _FakeKeyEvent(key_code=wx.WXK_F4, alt=True)
    PodcastsAppFrame._on_main_char_hook(frame, event)
    assert frame.tray_calls == [True]
    assert event.skipped is False


def test_cast_alt_f4_flows_through_when_disabled() -> None:
    frame = _cast_frame(alt_f4_to_tray=False)
    event = _FakeKeyEvent(key_code=wx.WXK_F4, alt=True)
    PodcastsAppFrame._on_main_char_hook(frame, event)
    assert frame.tray_calls == []
    assert event.skipped is True

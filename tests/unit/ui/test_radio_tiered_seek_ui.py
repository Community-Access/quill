"""Rewind and Forward by tap count, with a fake clock and a fake timer.

The burst only moves once, after it settles; what is said is where you landed;
and refusals come at the first press rather than after the wait.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.main_frame_radio import RadioMixin
from quill.ui.radio import bounded_playback_ui, tiered_seek_ui


class _Timer:
    def __init__(self, callback: Any) -> None:
        self.callback = callback
        self.stopped = False

    def Stop(self) -> None:  # noqa: N802 - wx's name
        self.stopped = True


class _Controller:
    def __init__(self, *, seekable: bool, station: object | None = "a station") -> None:
        self._seekable = seekable
        self.position = 600_000
        self.duration = 3_600_000
        self.skips: list[int] = []
        self.dvr: list[tuple[str, int]] = []
        self.behind = 0.0
        self.has_buffer = True
        self._station = station

    @property
    def state(self) -> Any:
        return type("S", (), {"station": self._station})()

    def is_seekable(self) -> bool:
        return self._seekable

    def skip_by(self, ms: int) -> bool:
        self.skips.append(ms)
        self.position = max(0, min(self.duration, self.position + ms))
        return True

    def duration_ms(self) -> int:
        return self.duration

    def current_chapter_index(self) -> int:
        return -1

    def chapters(self) -> list[object]:
        return []

    @property
    def _engine(self) -> Any:
        outer = self

        class _E:
            @staticmethod
            def position_ms() -> int:
                return outer.position

        return _E()

    def behind_live_seconds(self) -> float | None:
        return self.behind if self.has_buffer else None

    def rewind(self, seconds: int) -> float | None:
        self.dvr.append(("rewind", seconds))
        self.behind += seconds
        return self.behind

    def forward(self, seconds: int) -> float | None:
        self.dvr.append(("forward", seconds))
        self.behind = max(0.0, self.behind - seconds)
        return self.behind


class _Host:
    radio_rewind = RadioMixin.radio_rewind
    radio_forward = RadioMixin.radio_forward
    _radio_behind_live_phrase = staticmethod(RadioMixin._radio_behind_live_phrase)
    _radio_dvr_unavailable_message = RadioMixin._radio_dvr_unavailable_message

    def __init__(self, controller: _Controller) -> None:
        self._radio_controller = controller
        self.said: list[str] = []
        self.timers: list[_Timer] = []

    def tiered_seek_scheduler(self, _ms: int, callback: Any) -> _Timer:
        timer = _Timer(callback)
        self.timers.append(timer)
        return timer

    def fire(self) -> None:
        """The settle timer elapses: run the newest one that was not stopped."""
        live = [t for t in self.timers if not t.stopped]
        assert live, "no settle timer is pending"
        live[-1].callback()

    def _announce(self, text: str) -> None:
        self.said.append(text)


def _press(host: _Host, direction: int, at: float) -> None:
    tiered_seek_ui.press(host, direction, tiered_seek_ui.apply_main, now=at)


class _Clock:
    """Deliberate taps: each reading is 0.2 seconds after the last."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        self.now += 0.2
        return self.now


@pytest.fixture
def tapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tiered_seek_ui, "time", _Clock())


def test_nothing_moves_until_the_burst_settles() -> None:
    host = _Host(_Controller(seekable=True))
    _press(host, -1, 0.0)
    _press(host, -1, 0.2)
    assert host._radio_controller.skips == []
    host.fire()
    assert host._radio_controller.skips == [-60_000], "two taps are one minute, once"


def test_three_taps_are_five_minutes_in_one_seek() -> None:
    host = _Host(_Controller(seekable=True))
    for at in (0.0, 0.2, 0.4):
        _press(host, 1, at)
    host.fire()
    assert host._radio_controller.skips == [300_000]
    assert host.said == ["15 minutes of 1 hour"]


def test_a_hold_moves_five_seconds_per_repeat() -> None:
    host = _Host(_Controller(seekable=True))
    for index in range(6):
        _press(host, -1, index * 0.033)
    host.fire()
    assert host._radio_controller.skips == [-30_000]


def test_each_press_restarts_the_wait() -> None:
    host = _Host(_Controller(seekable=True))
    _press(host, 1, 0.0)
    _press(host, 1, 0.2)
    assert host.timers[0].stopped and not host.timers[1].stopped


def test_changing_direction_settles_the_first_burst() -> None:
    host = _Host(_Controller(seekable=True))
    _press(host, -1, 0.0)
    _press(host, -1, 0.2)
    _press(host, 1, 0.4)
    host.fire()
    assert host._radio_controller.skips == [-60_000, 12_000]


def test_live_radio_says_how_far_behind_not_how_far_moved() -> None:
    host = _Host(_Controller(seekable=False))
    _press(host, -1, 0.0)
    _press(host, -1, 0.2)
    host.fire()
    assert host._radio_controller.dvr == [("rewind", 60)]
    assert host.said == ["1 minute behind live."]
    assert "rewound" not in " ".join(host.said).casefold()


def test_the_main_window_keys_are_tiered(tapping: None) -> None:
    host = _Host(_Controller(seekable=False))
    host.radio_rewind()
    host.radio_rewind()
    host.fire()
    assert host._radio_controller.dvr == [("rewind", 60)]


def test_nothing_playing_is_said_at_the_first_press() -> None:
    host = _Host(_Controller(seekable=False, station=None))
    host.radio_rewind()
    assert host.said == ["Nothing is playing."]
    assert host.timers == [], "no wait: a refusal must not come half a second late"


def test_no_buffer_is_said_at_the_first_press() -> None:
    controller = _Controller(seekable=False)
    controller.has_buffer = False
    host = _Host(controller)
    host.radio_forward()
    assert "mpv" in host.said[0]
    assert host.timers == []


def test_without_a_timer_one_press_is_one_tap() -> None:
    """No wx app and no scheduler: settle at once rather than never."""

    class _Bare:
        def __init__(self) -> None:
            self._radio_controller = _Controller(seekable=True)
            self.said: list[str] = []

        def _announce(self, text: str) -> None:
            self.said.append(text)

    host = _Bare()
    import wx

    if wx.GetApp() is not None:  # another test left an app: use the scheduler path
        host.tiered_seek_scheduler = lambda _ms, callback: callback()  # type: ignore[attr-defined]
    tiered_seek_ui.press(host, 1, tiered_seek_ui.apply_timeline)
    assert host._radio_controller.skips == [12_000]


def test_the_browse_window_skip_keys_are_tiered_too(tapping: None) -> None:
    host = _Host(_Controller(seekable=True))
    bounded_playback_ui.skip_back(host)
    bounded_playback_ui.skip_back(host)
    host.fire()
    assert host._radio_controller.skips == [-60_000]

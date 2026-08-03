"""Quill Radio's earcons fire on real state changes, once each (#1302).

Two halves. The playback states (connecting / playing / stopped / stream
error) are cued by ``RadioPlayerController._set_state``, which is the only
place that knows a stream reached the air, so those are driven through a real
controller with a fake engine. Everything the app already speaks -- buffering,
recording started/stopped, favourite added -- carries its cue on the existing
``_announce`` call, so those are driven through ``RadioMixin`` against a fake
``_announce`` that captures the ``sound`` keyword. No audio hardware.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core.radio.models import RadioStation
from quill.core.sound_events import SoundEvent
from quill.ui.main_frame_radio import RadioMixin
from quill.ui.radio.player_controller import RadioPlayerController, RadioPlayerState


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self, *, loads: bool = True) -> None:
        self._loads = loads

    def load(self, _source: str) -> bool:
        return self._loads

    def play(self) -> None: ...
    def pause(self) -> None: ...
    def close(self) -> None: ...
    def set_volume(self, _percent: int) -> None: ...


def _controller(monkeypatch: pytest.MonkeyPatch, *, loads: bool = True):
    """A controller wired to a fake engine, plus the list of cues it posted."""
    cues: list[str] = []
    monkeypatch.setattr("quill.ui.radio.player_controller.post_cue", cues.append)
    frame = wx.Frame(None)
    # playback_engine="wx" pins the classic backend so the injected fake is
    # used even where libmpv is installed.
    controller = RadioPlayerController(frame, playback_engine="wx")
    fake = _FakeEngine(loads=loads)
    controller._wx_engine = fake
    controller._engine = fake
    return controller, cues


def _station(name: str = "Station A") -> RadioStation:
    return RadioStation(name=name, stream_url=f"http://example.test/{name}")


# -- playback states -------------------------------------------------------


def test_play_cues_connecting_then_playing(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, cues = _controller(monkeypatch)
    controller.play_station(_station())
    assert cues == [SoundEvent.RADIO_CONNECTING]
    controller._on_loaded(0)
    assert cues == [SoundEvent.RADIO_CONNECTING, SoundEvent.RADIO_PLAYING]


def test_stop_cues_stopped_and_a_second_stop_stays_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, cues = _controller(monkeypatch)
    controller.play_station(_station())
    controller._on_loaded(0)
    cues.clear()
    controller.stop()
    assert cues == [SoundEvent.RADIO_STOPPED]
    controller.stop()
    assert cues == [SoundEvent.RADIO_STOPPED]


def test_a_stream_that_cannot_open_cues_the_error_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, cues = _controller(monkeypatch, loads=False)
    monkeypatch.setattr(controller, "_attempt_engine_fallback", lambda: False)
    controller.play_station(_station())
    assert cues == [SoundEvent.RADIO_CONNECTING, SoundEvent.RADIO_STREAM_ERROR]
    # The recovery ladder re-declares the same failure: no second earcon.
    controller._on_error("still broken")
    assert cues.count(SoundEvent.RADIO_STREAM_ERROR) == 1


def test_pausing_has_no_earcon(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, cues = _controller(monkeypatch)
    controller.play_station(_station())
    controller._on_loaded(0)
    cues.clear()
    controller.toggle_play_pause()
    assert controller.state.state is RadioPlayerState.PAUSED
    assert cues == []


def test_volume_changes_do_not_cue(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, cues = _controller(monkeypatch)
    controller.play_station(_station())
    controller._on_loaded(0)
    cues.clear()
    controller.set_volume(30)
    controller.toggle_mute()
    assert cues == []


# -- announcements that carry a cue ---------------------------------------


class _Host(RadioMixin):
    """Just enough RadioMixin host to drive the announcement call sites."""

    def __init__(self) -> None:
        self.spoken: list[tuple[str, str]] = []

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.spoken.append((message, sound))

    def _refresh_statusbar(self) -> None: ...
    def _refresh_radio_tray_tooltip(self) -> None: ...
    def _update_sleep_inhibitor(self) -> None: ...
    def _radio_track_history_and_volume(self, _state: Any) -> None: ...
    def _radio_track_titles_follow_playback(self, _state: Any) -> None: ...
    def _radio_maybe_try_fallback_url(self, _state: Any) -> None: ...
    def _persist_radio_recording_marker(self, _job_id: str = "") -> None: ...
    def _clear_radio_recording_marker(self, _job_id: str | None = None) -> None: ...


def _host() -> _Host:
    return _Host()


def test_buffering_cues_once_until_the_playback_state_changes() -> None:
    host = _host()
    host._radio_announce_buffering()
    host._radio_announce_buffering()
    host._radio_announce_buffering()
    assert [sound for _msg, sound in host.spoken] == [SoundEvent.RADIO_BUFFERING, "", ""]
    assert all(msg == "Buffering..." for msg, _sound in host.spoken)


def test_a_new_playback_state_re_arms_the_buffering_cue() -> None:
    host = _host()
    host._radio_announce_buffering()
    host._on_radio_state_changed(SimpleNamespace(state=RadioPlayerState.CONNECTING, station=None))
    host._radio_announce_buffering()
    assert [sound for _msg, sound in host.spoken] == [
        SoundEvent.RADIO_BUFFERING,
        SoundEvent.RADIO_BUFFERING,
    ]


def test_a_volume_notification_does_not_re_arm_the_buffering_cue() -> None:
    host = _host()
    host._radio_announce_buffering()
    state = SimpleNamespace(state=RadioPlayerState.PLAYING, station=None)
    host._on_radio_state_changed(state)  # first sighting of PLAYING re-arms
    host._radio_announce_buffering()
    host._on_radio_state_changed(state)  # a volume/mute notify: same state
    host._radio_announce_buffering()
    assert [sound for _msg, sound in host.spoken] == [
        SoundEvent.RADIO_BUFFERING,
        SoundEvent.RADIO_BUFFERING,
        "",
    ]


def test_a_finished_recording_cues_recording_stopped() -> None:
    host = _host()
    host._apply_radio_recording_changed(False, Path("show.mp3"), "job-1")
    assert host.spoken == [("Recording saved: show.mp3", SoundEvent.RADIO_RECORDING_STOPPED)]


def test_a_scheduled_recording_starting_cues_recording_started() -> None:
    host = _host()
    host._apply_radio_scheduled_recording_fired(SimpleNamespace(station_name="WXYZ"), "")
    assert host.spoken == [
        ("Scheduled recording started: WXYZ", SoundEvent.RADIO_RECORDING_STARTED)
    ]


def test_a_failed_scheduled_recording_gets_no_start_cue() -> None:
    host = _host()
    host._apply_radio_scheduled_recording_fired(SimpleNamespace(station_name="WXYZ"), "no ffmpeg")
    assert host.spoken[0][1] == ""


class _Favorites:
    def __init__(self) -> None:
        self.saved: list[Any] = []

    def contains(self, _station: Any) -> bool:
        return bool(self.saved)

    def add(self, station: Any) -> None:
        self.saved.append(station)

    def remove(self, _key: str) -> None:
        self.saved.clear()


def test_the_standalone_app_cues_a_station_added_to_favourites() -> None:
    from quill.apps.radio import RadioAppFrame

    app = RadioAppFrame.__new__(RadioAppFrame)
    spoken: list[tuple[str, str]] = []
    app._announce = lambda message, *, force=False, sound="": spoken.append((message, sound))
    app._radio_controller = SimpleNamespace(state=SimpleNamespace(station=_station("KEXP")))
    app._radio_favorites = _Favorites()
    app._save_radio_favorites = lambda: None
    app._reload_favorites_tree = lambda: None
    app._refresh_favorite_toggle = lambda: None
    app._on_favorite_toggle()
    assert spoken == [("Added KEXP to favorites", SoundEvent.RADIO_FAVORITE_ADDED)]
    # Removing one is not the same event and must not borrow its cue.
    spoken.clear()
    app._on_favorite_toggle()
    assert spoken == [("Removed KEXP from favorites", "")]

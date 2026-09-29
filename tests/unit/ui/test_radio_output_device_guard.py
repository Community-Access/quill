"""The output device is a promise the radio keeps, or says out loud that it cannot.

Reported 2026-09-28: "changing the sound card in the Audio menu is not
switching to a different card". libmpv switches devices at runtime and on
reload (probed on a real machine the same day), and the controller hands the
device to it -- so the sound stays on the old card only when the mpv engine
fails to *open* the chosen device (a headset asleep, an id that changed, a
device another app holds) and the app quietly falls back to Windows Media,
which can only play on the system default. Nothing was said and nothing was
logged (testkspn.md). These tests pin the new behaviour
(``quill/ui/radio/output_device_guard.py``):

* a playing mpv station switches device *live*, without a reconnect;
* a load that fails with a device chosen is retried once on the system
  default, still on mpv, and the listener is told which device could not be
  opened;
* the device is watched for, and playback returns to it, with a word, the
  moment it is offered again;
* falling back to Windows Media with a device chosen is said, not hidden.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

import quill.ui.radio.engine_selection as engine_selection
from quill.core.radio.models import RadioStation
from quill.ui.radio import output_device_guard as guard
from quill.ui.radio.playback_state import RadioPlayerState
from quill.ui.radio.player_controller import RadioPlayerController

HEADSET = "wasapi/{aaaa}"
SPEAKERS = "wasapi/{bbbb}"
DEVICES = [(HEADSET, "Speakers (Logi USB Headset)"), (SPEAKERS, "Speakers (Realtek)")]


class _FakeMpv:
    """An mpv engine stand-in that refuses to load while ``fail_devices`` names its device."""

    def __init__(self) -> None:
        self.loads: list[tuple[str, str]] = []  # (url, device at the time)
        self.devices: list[str] = []
        self.device = ""
        self.fail_devices: set[str] = set()
        self.closed = 0
        self.filter_graphs: list[str] = []
        self.pending_error: bool = False

    def set_audio_device(self, name: str) -> None:
        self.device = name.strip()
        self.devices.append(self.device)

    def load(self, source: str) -> bool:
        self.loads.append((source, self.device))
        self.pending_error = self.device in self.fail_devices
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        self.closed += 1

    def set_volume(self, percent: int) -> None:
        pass

    def set_filter_graph(self, graph: str) -> None:
        self.filter_graphs.append(graph)


class _FakeWx:
    def __init__(self) -> None:
        self.loads: list[str] = []

    def load(self, source: str) -> bool:
        self.loads.append(source)
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        pass

    def set_volume(self, percent: int) -> None:
        pass


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def radio(wx_app, monkeypatch: pytest.MonkeyPatch):
    """A controller on mpv, with the device list under the test's control."""
    monkeypatch.setattr(engine_selection, "mpv_output_device_available", lambda: True)
    offered = {"devices": list(DEVICES)}
    monkeypatch.setattr(guard, "list_audio_devices", lambda: list(offered["devices"]))
    said: list[str] = []
    later: list[tuple[int, Any]] = []
    frame = wx.Frame(None)
    controller = RadioPlayerController(
        frame,
        output_device=HEADSET,
        playback_engine="mpv",
        on_output_device_error=said.append,
    )
    mpv = _FakeMpv()
    wxe = _FakeWx()
    controller._wx_engine = wxe
    controller._engine = wxe
    controller._mpv_engine = mpv
    monkeypatch.setattr(controller, "_schedule_later", lambda ms, work: later.append((ms, work)))

    def finish_load() -> None:
        """Deliver mpv's verdict on the last load, the way the poll would."""
        if mpv.pending_error:
            mpv.pending_error = False
            controller._on_error("That stream could not be opened.")
        else:
            controller._on_loaded(0)

    return {
        "controller": controller,
        "mpv": mpv,
        "wx": wxe,
        "said": said,
        "later": later,
        "offered": offered,
        "finish": finish_load,
        "frame": frame,
    }


def _station() -> RadioStation:
    return RadioStation(name="KSPN", stream_url="http://example.test/kspn")


def test_a_playing_mpv_station_switches_device_live_without_a_reconnect(radio) -> None:
    c, mpv = radio["controller"], radio["mpv"]
    c.play_station(_station())
    radio["finish"]()
    assert c.state.state is RadioPlayerState.PLAYING
    loads_before = len(mpv.loads)
    c.set_output_device(SPEAKERS)
    assert mpv.devices[-1] == SPEAKERS
    assert len(mpv.loads) == loads_before  # no reconnect: mpv re-opens the AO itself
    assert c.state.state is RadioPlayerState.PLAYING


def test_a_device_that_will_not_open_falls_to_the_default_on_mpv_and_says_so(radio) -> None:
    c, mpv, said = radio["controller"], radio["mpv"], radio["said"]
    mpv.fail_devices = {HEADSET}
    c.play_station(_station())
    radio["finish"]()  # the load with the headset fails
    # Retried at once on mpv with the system default, not on Windows Media.
    assert mpv.loads[-1][1] == ""
    assert radio["wx"].loads == []
    radio["finish"]()
    assert c.state.state is RadioPlayerState.PLAYING
    assert said == [
        "Speakers (Logi USB Headset) could not be opened. Playing on the system "
        "default until it is available again."
    ]
    assert c.output_device_fallback_active is True
    # The preference itself is untouched: the choice stands.
    assert c.output_device == HEADSET


def test_the_device_is_watched_for_and_playback_returns_to_it(radio) -> None:
    c, mpv, said, later = radio["controller"], radio["mpv"], radio["said"], radio["later"]
    mpv.fail_devices = {HEADSET}
    radio["offered"]["devices"] = [(SPEAKERS, "Speakers (Realtek)")]  # headset gone
    c.play_station(_station())
    radio["finish"]()
    radio["finish"]()
    assert later, "a watcher was scheduled"
    delay, check = later[-1]
    assert delay >= 5000
    check()  # still gone: keep watching, say nothing more
    assert len(said) == 1
    assert len(later) == 2
    radio["offered"]["devices"] = list(DEVICES)  # plugged back in
    mpv.fail_devices = set()
    _delay, check = later[-1]
    check()
    assert mpv.devices[-1] == HEADSET  # switched back live, no reconnect
    assert c.output_device_fallback_active is False
    assert said[-1] == "Speakers (Logi USB Headset) is available again. Playing on it."
    assert len(later) == 2  # the watch is over


def test_choosing_another_device_ends_the_watch(radio) -> None:
    c, mpv, later = radio["controller"], radio["mpv"], radio["later"]
    mpv.fail_devices = {HEADSET}
    c.play_station(_station())
    radio["finish"]()
    radio["finish"]()
    assert c.output_device_fallback_active
    c.set_output_device(SPEAKERS)
    assert c.output_device_fallback_active is False
    _delay, check = later[-1]
    check()  # the old watch wakes up and does nothing
    assert mpv.devices[-1] == SPEAKERS


def test_a_stream_that_fails_on_both_devices_is_a_stream_problem(radio) -> None:
    """The rescue is one retry: a URL mpv cannot play at all still reaches the
    Windows Media fallback -- and with a device chosen, that is said too."""
    c, mpv, said = radio["controller"], radio["mpv"], radio["said"]
    mpv.fail_devices = {HEADSET, ""}
    c.play_station(_station())
    radio["finish"]()  # headset fails -> retry on default
    radio["finish"]()  # default fails too -> Windows Media
    assert radio["wx"].loads == ["http://example.test/kspn"]
    assert said[-1] == (
        "Windows Media is playing this station, and it cannot use the chosen "
        "output device; the audio is on the system default."
    )
    assert c.output_device_fallback_active is False


def test_the_device_switch_is_logged(radio, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    c = radio["controller"]
    with caplog.at_level(logging.INFO, logger="quill.ui.radio.output_device_guard"):
        c.play_station(_station())
        radio["finish"]()
        c.set_output_device(SPEAKERS)
    assert any("Speakers (Realtek)" in r.getMessage() for r in caplog.records)


def test_device_label_falls_back_to_the_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guard, "list_audio_devices", lambda: [])
    assert guard.device_label("wasapi/{zzzz}") == "wasapi/{zzzz}"
    monkeypatch.setattr(guard, "list_audio_devices", lambda: list(DEVICES))
    assert guard.device_label(HEADSET) == "Speakers (Logi USB Headset)"
    assert guard.device_label("") == "the system default"

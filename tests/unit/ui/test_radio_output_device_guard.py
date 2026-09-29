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
* a load that fails with a device chosen is retried once, still on mpv, on the
  device in use before the choice, the listener is told, and the setting goes
  back to that device (Jeff, 2026-09-29: revert, do not keep a choice that
  cannot be honoured);
* a saved device that will not open at start-up is reverted the same way;
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


def _make(monkeypatch: pytest.MonkeyPatch, *, output_device: str) -> dict[str, Any]:
    monkeypatch.setattr(engine_selection, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(guard, "list_audio_devices", lambda: list(DEVICES))
    said: list[str] = []
    saved: list[str] = []
    frame = wx.Frame(None)
    controller = RadioPlayerController(
        frame,
        output_device=output_device,
        playback_engine="mpv",
        on_output_device_error=said.append,
    )
    controller.on_output_device_reverted = saved.append
    mpv = _FakeMpv()
    wxe = _FakeWx()
    controller._wx_engine = wxe
    controller._engine = wxe
    controller._mpv_engine = mpv

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
        "saved": saved,
        "finish": finish_load,
    }


@pytest.fixture
def radio(wx_app, monkeypatch: pytest.MonkeyPatch):
    """A controller on mpv playing on the system default, the device list fixed."""
    return _make(monkeypatch, output_device="")


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
    assert c.output_device == SPEAKERS


def test_a_device_that_will_not_open_is_given_back_and_said(radio) -> None:
    """Playing on the default, the headset is chosen and fails to open: the sound
    stays on mpv, the setting goes back to the default, and the listener hears both."""
    c, mpv, said, saved = radio["controller"], radio["mpv"], radio["said"], radio["saved"]
    c.play_station(_station())
    radio["finish"]()
    mpv.fail_devices = {HEADSET}
    # A live switch does not reload; the failure shows up as the next load
    # failing (the engine reports the dead audio output as end of stream, and
    # the reconnect reloads with the device still set).
    c.set_output_device(HEADSET)
    c.play_station(_station())  # the reconnect the engine's EOF triggers
    radio["finish"]()  # ...fails on the headset
    assert mpv.loads[-1][1] == ""  # retried at once on mpv, on the default
    assert radio["wx"].loads == []
    radio["finish"]()
    assert c.state.state is RadioPlayerState.PLAYING
    assert said[-1] == (
        "Speakers (Logi USB Headset) could not be opened, so the output device is back to "
        "System default."
    )
    assert c.output_device == ""  # the setting itself reverted...
    assert saved == [""]  # ...and the host was asked to persist it


def test_the_revert_goes_to_the_device_in_use_before_not_the_default(radio) -> None:
    c, mpv, said = radio["controller"], radio["mpv"], radio["said"]
    c.play_station(_station())
    radio["finish"]()
    c.set_output_device(SPEAKERS)  # fine
    mpv.fail_devices = {HEADSET}
    c.set_output_device(HEADSET)  # fails
    c.play_station(_station())
    radio["finish"]()
    assert mpv.loads[-1][1] == SPEAKERS
    assert c.output_device == SPEAKERS
    assert said == []  # not yet: the retry has not answered
    radio["finish"]()  # the speakers play, so the headset was the problem
    assert said[-1].endswith("is back to Speakers (Realtek).")


def test_a_saved_device_that_will_not_open_at_startup_reverts_to_the_default(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    radio = _make(monkeypatch, output_device=HEADSET)
    c, mpv, said, saved = radio["controller"], radio["mpv"], radio["said"], radio["saved"]
    mpv.fail_devices = {HEADSET}
    c.play_station(_station())
    radio["finish"]()  # the headset fails
    assert mpv.loads[-1][1] == ""
    radio["finish"]()
    assert c.state.state is RadioPlayerState.PLAYING
    assert c.output_device == ""
    assert saved == [""]
    assert "back to System default" in said[-1]


def test_a_stream_that_fails_on_both_devices_is_a_stream_problem(radio) -> None:
    """The rescue is one retry: a URL mpv cannot play at all still reaches the
    Windows Media fallback -- and with a device chosen, that is said too."""
    c, mpv, said = radio["controller"], radio["mpv"], radio["said"]
    c.play_station(_station())
    radio["finish"]()
    c.set_output_device(SPEAKERS)
    mpv.fail_devices = {HEADSET, SPEAKERS, ""}
    c.set_output_device(HEADSET)
    c.play_station(_station())
    radio["finish"]()  # headset fails -> back to the speakers
    radio["finish"]()  # speakers fail too -> Windows Media
    assert radio["wx"].loads == ["http://example.test/kspn"]
    assert said[-1] == (
        "Windows Media is playing this station, and it cannot use the chosen "
        "output device; the audio is on the device Windows gives Quill Radio."
    )
    # The stream was the problem, not the headset: the choice stands, unsaid.
    assert c.output_device == HEADSET
    assert not any("could not be opened" in s for s in said)


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
    assert guard.device_label("") == "System default"


def test_switching_the_engine_to_windows_media_gives_a_chosen_device_back(radio) -> None:
    """Windows Media cannot route (no documented device selection), so a device
    chosen under it is given back with the way to use one named."""
    c, said, saved = radio["controller"], radio["said"], radio["saved"]
    c.play_station(_station())
    radio["finish"]()
    c.set_output_device(SPEAKERS)
    c.set_playback_engine("wx")
    assert c.output_device == ""
    assert saved == [""]
    assert said[-1] == (
        "Windows Media (classic) plays on the device Windows gives Quill Radio, so the output "
        "device is back to System default. To send it to Speakers (Realtek), choose Quill "
        "Radio's output device in Windows' Sound settings, under Volume mixer."
    )


def test_a_saved_device_under_windows_media_is_given_back_at_the_first_play(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_selection, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(guard, "list_audio_devices", lambda: list(DEVICES))
    said: list[str] = []
    saved: list[str] = []
    frame = wx.Frame(None)
    c = RadioPlayerController(
        frame, output_device=SPEAKERS, playback_engine="wx", on_output_device_error=said.append
    )
    c.on_output_device_reverted = saved.append
    wxe = _FakeWx()
    c._wx_engine = wxe
    c._engine = wxe
    c.play_station(_station())
    assert wxe.loads == ["http://example.test/kspn"]
    assert c.output_device == "" and saved == [""]
    assert said and said[-1].startswith("Windows Media (classic) plays on the device Windows")


# -- the modern Windows Media engine routes too (2026-09-29) --------------------------


class _FakeRoutingWx(_FakeWx):
    """The modern Windows Media engine: the classic fake plus set_audio_device."""

    def __init__(self) -> None:
        super().__init__()
        self.devices: list[str] = []

    def set_audio_device(self, name: str) -> None:
        self.devices.append(name)


def _make_windows(monkeypatch: pytest.MonkeyPatch, *, output_device: str) -> dict[str, Any]:
    """A controller with no libmpv and the modern Windows engine."""
    monkeypatch.setattr(engine_selection, "mpv_output_device_available", lambda: False)
    monkeypatch.setattr(guard, "list_audio_devices", lambda: list(DEVICES))
    said: list[str] = []
    saved: list[str] = []
    frame = wx.Frame(None)
    controller = RadioPlayerController(
        frame,
        output_device=output_device,
        playback_engine="wx",
        on_output_device_error=said.append,
    )
    controller.on_output_device_reverted = saved.append
    wxe = _FakeRoutingWx()
    controller._wx_engine = wxe
    controller._engine = wxe
    return {"controller": controller, "wx": wxe, "said": said, "saved": saved}


def test_the_windows_engine_takes_a_chosen_device_and_nothing_is_reverted(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = _make_windows(monkeypatch, output_device=SPEAKERS)
    c, wxe = r["controller"], r["wx"]
    c.play_station(_station())
    assert wxe.loads == ["http://example.test/kspn"]
    assert wxe.devices[-1] == SPEAKERS
    assert c.output_device == SPEAKERS
    assert r["saved"] == [] and r["said"] == []


def test_the_windows_engine_switches_device_live(wx_app, monkeypatch: pytest.MonkeyPatch) -> None:
    r = _make_windows(monkeypatch, output_device="")
    c, wxe = r["controller"], r["wx"]
    c.play_station(_station())
    c._on_loaded(0)
    assert c.state.state is RadioPlayerState.PLAYING
    c.set_output_device(HEADSET)
    assert wxe.devices[-1] == HEADSET
    assert wxe.loads == ["http://example.test/kspn"]  # no reconnect
    assert c.state.state is RadioPlayerState.PLAYING
    assert r["said"] == []


def test_a_device_the_windows_engine_cannot_open_is_given_back_on_the_same_engine(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = _make_windows(monkeypatch, output_device=HEADSET)
    c, wxe, said, saved = r["controller"], r["wx"], r["said"], r["saved"]
    c.play_station(_station())
    assert wxe.devices[-1] == HEADSET
    c._on_error("The device would not open.")  # the engine's verdict on the load
    assert wxe.loads == ["http://example.test/kspn"] * 2  # retried, still on Windows Media
    assert wxe.devices[-1] == ""
    assert said == [] and saved == []  # the verdict waits for the retry
    c._on_loaded(0)  # the default plays: the headset was the problem
    assert c.output_device == ""
    assert saved == [""]
    assert said[-1] == (
        "Speakers (Logi USB Headset) could not be opened, so the output device is back to "
        "System default."
    )


def test_switching_to_windows_media_keeps_the_device_when_the_engine_routes(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_selection, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(guard, "list_audio_devices", lambda: list(DEVICES))
    said: list[str] = []
    saved: list[str] = []
    frame = wx.Frame(None)
    c = RadioPlayerController(
        frame, output_device=SPEAKERS, playback_engine="auto", on_output_device_error=said.append
    )
    c.on_output_device_reverted = saved.append
    mpv, wxe = _FakeMpv(), _FakeRoutingWx()
    c._mpv_engine, c._wx_engine, c._engine = mpv, wxe, mpv
    c.play_station(_station())
    c._on_loaded(0)
    c.set_playback_engine("wx")
    assert c.output_device == SPEAKERS and saved == [] and said == []
    assert wxe.devices[-1] == SPEAKERS
    assert wxe.loads == ["http://example.test/kspn"]


def test_the_rescue_onto_the_windows_engine_carries_the_device(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mpv cannot play the stream at all: Windows Media takes it, on the same
    device, and nobody is told the device was lost -- because it was not."""
    monkeypatch.setattr(engine_selection, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(guard, "list_audio_devices", lambda: list(DEVICES))
    said: list[str] = []
    frame = wx.Frame(None)
    c = RadioPlayerController(
        frame, output_device=SPEAKERS, playback_engine="mpv", on_output_device_error=said.append
    )
    mpv, wxe = _FakeMpv(), _FakeRoutingWx()
    c._mpv_engine, c._wx_engine, c._engine = mpv, wxe, mpv
    c.play_station(_station())
    c._on_error("no")  # the stream fails on the speakers: retried on the default, still mpv
    assert mpv.loads[-1][1] == ""
    c._on_error("no")  # and on the default: the stream is the problem -> Windows Media
    assert wxe.loads == ["http://example.test/kspn"]
    assert c.output_device == SPEAKERS  # restored: the speakers were never at fault
    assert wxe.devices[-1] == SPEAKERS  # and Windows Media plays on them
    assert said == []


def test_windows_engine_routes_reads_the_engine_not_the_preference() -> None:
    class _Host:
        _wx_engine = _FakeRoutingWx()

    class _Classic:
        _wx_engine = _FakeWx()

    assert guard.windows_engine_routes(_Host()) is True
    assert guard.windows_engine_routes(_Classic()) is False
    assert guard.windows_engine_routes(object()) is False

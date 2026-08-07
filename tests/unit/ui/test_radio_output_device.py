"""Radio output-device selection (#1076): the live-stream mpv state machine,
device-list parsing, the Preferences dropdown model, and the controller's
strict opt-in engine switching -- all headless (no libmpv, no network)."""

from __future__ import annotations

import pytest
import wx

from quill.core.radio.models import RadioStation
from quill.ui.radio import mpv_radio_engine
from quill.ui.radio.mpv_radio_engine import (
    ACTION_ERROR,
    ACTION_FINISHED,
    ACTION_LOADED,
    ACTION_NONE,
    next_poll_action,
    output_device_choices,
    parse_audio_device_list,
)
from quill.ui.radio.player_controller import RadioPlayerController, RadioPlayerState


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


# -- next_poll_action: the live-stream readiness state machine ----------------


def test_connecting_stays_quiet_while_mpv_works() -> None:
    action = next_poll_action(loaded=False, idle_active=False, core_idle=True, eof_reached=False)
    assert action == ACTION_NONE


def test_core_leaving_idle_means_the_stream_is_ready() -> None:
    # This is the live-stream replacement for the audiobook engine's
    # duration gate: a live stream never reports a duration, but core-idle
    # goes false the moment audio is actually being output.
    action = next_poll_action(loaded=False, idle_active=False, core_idle=False, eof_reached=False)
    assert action == ACTION_LOADED


def test_falling_back_to_idle_before_loaded_is_an_error() -> None:
    action = next_poll_action(loaded=False, idle_active=True, core_idle=True, eof_reached=False)
    assert action == ACTION_ERROR


def test_eof_after_loaded_means_the_connection_dropped() -> None:
    action = next_poll_action(loaded=True, idle_active=False, core_idle=True, eof_reached=True)
    assert action == ACTION_FINISHED


def test_idle_after_loaded_also_means_disconnected() -> None:
    action = next_poll_action(loaded=True, idle_active=True, core_idle=None, eof_reached=None)
    assert action == ACTION_FINISHED


def test_failed_property_reads_never_drive_a_transition() -> None:
    for loaded in (False, True):
        action = next_poll_action(loaded=loaded, idle_active=None, core_idle=None, eof_reached=None)
        assert action == ACTION_NONE


def test_playing_normally_stays_quiet() -> None:
    action = next_poll_action(loaded=True, idle_active=False, core_idle=False, eof_reached=False)
    assert action == ACTION_NONE


# -- parse_audio_device_list ---------------------------------------------------


_REAL_SHAPE = (
    '[{"name":"auto","description":"Autoselect device"},'
    '{"name":"wasapi/{aaa}","description":"Speakers (Logi USB Headset)"},'
    '{"name":"wasapi/{bbb}","description":"Speakers (Realtek High Definition Audio)"},'
    '{"name":"openal","description":"Default (openal)"}]'
)


def test_parse_device_list_keeps_real_devices_only() -> None:
    devices = parse_audio_device_list(_REAL_SHAPE)
    # "auto" duplicates System default and bare driver fallbacks (openal)
    # are not sound cards; only pickable devices survive.
    assert devices == [
        ("wasapi/{aaa}", "Speakers (Logi USB Headset)"),
        ("wasapi/{bbb}", "Speakers (Realtek High Definition Audio)"),
    ]


def test_parse_device_list_survives_malformed_input() -> None:
    assert parse_audio_device_list("not json") == []
    assert parse_audio_device_list("{}") == []
    assert parse_audio_device_list('[{"description":"nameless"},42]') == []


def test_parse_device_list_falls_back_to_name_when_description_missing() -> None:
    assert parse_audio_device_list('[{"name":"wasapi/{x}"}]') == [("wasapi/{x}", "wasapi/{x}")]


def test_list_audio_devices_empty_without_libmpv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mpv_radio_engine, "find_libmpv", lambda: None)
    assert mpv_radio_engine.list_audio_devices() == []
    assert mpv_radio_engine.mpv_output_device_available() is False


# -- the Preferences dropdown model --------------------------------------------


_DEVICES = [
    ("wasapi/{aaa}", "Speakers (Logi USB Headset)"),
    ("wasapi/{bbb}", "Speakers (Realtek High Definition Audio)"),
]


def test_choices_put_system_default_first_and_selected() -> None:
    labels, names, index = output_device_choices(_DEVICES, "")
    assert labels[0] == "System default"
    assert names[0] == ""
    assert index == 0
    assert labels[1:] == [d[1] for d in _DEVICES]
    assert names[1:] == [d[0] for d in _DEVICES]


def test_choices_select_the_saved_device() -> None:
    _labels, names, index = output_device_choices(_DEVICES, "wasapi/{bbb}")
    assert names[index] == "wasapi/{bbb}"


def test_unplugged_saved_device_is_kept_not_reset() -> None:
    # A USB sound card that is unplugged today must not be silently
    # dropped just because Preferences was opened.
    labels, names, index = output_device_choices(_DEVICES, "wasapi/{gone}")
    assert names[index] == "wasapi/{gone}"
    assert "not currently available" in labels[index]


# -- controller: strict opt-in engine switching ---------------------------------


class _FakeEngine:
    def __init__(self) -> None:
        self.loads: list[str] = []
        self.closed = False

    def load(self, source: str) -> bool:
        self.loads.append(source)
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def set_volume(self, percent: int) -> None:
        pass

    def set_audio_device(self, name: str) -> None:
        pass


def _station(name: str = "Station A") -> RadioStation:
    return RadioStation(name=name, stream_url=f"http://example.test/{name}")


def test_wx_mode_never_touches_mpv(monkeypatch: pytest.MonkeyPatch) -> None:
    # The escape hatch: "Windows Media (classic)" pins the wx engine and
    # never consults the mpv path, even with libmpv installed.
    #
    # The wx engine is monkeypatched at the class (same pattern as the mpv
    # test below): constructing a REAL WMP10 ActiveX MediaCtrl here is
    # incidental to what the test proves, and on wxPython 4.3 doing so deep
    # into a long test run access-violates on COM state some earlier test
    # left behind (passes in isolation; native crash in the full suite).
    import quill.ui.radio.player_controller as pc

    fake = _FakeEngine()
    monkeypatch.setattr(pc, "WxMediaEngine", lambda *a, **k: fake)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="wx")
    controller.play_station(_station())
    assert fake.loads  # played through the (injected) wx engine
    assert controller._mpv_engine is None


def test_auto_mode_prefers_mpv_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    # "auto" = mpv whenever libmpv is present (device routing, live
    # pause/rewind, Volume Boost, Ogg/Opus/HLS all need it), wx otherwise.
    import quill.ui.radio.player_controller as pc

    fake_mpv = _FakeEngine()
    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(pc, "MpvRadioEngine", lambda *a, **k: fake_mpv)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame)  # default: auto
    controller.play_station(_station())
    assert fake_mpv.loads  # played through the (faked) mpv engine
    assert controller._engine is fake_mpv


def test_auto_mode_uses_wx_when_libmpv_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.ui.radio.player_controller as pc

    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: False)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame)
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    controller.play_station(_station())
    assert fake.loads
    assert controller._mpv_engine is None


def test_device_with_no_libmpv_falls_back_with_announcement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.ui.radio.player_controller as pc

    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: False)
    announced: list[str] = []
    frame = wx.Frame(None)
    controller = RadioPlayerController(
        frame,
        output_device="wasapi/{aaa}",
        on_output_device_error=announced.append,
    )
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    controller.play_station(_station())
    assert fake.loads  # playback proceeded on the default engine
    assert announced and "system default" in announced[0]


def test_device_switch_reconnects_the_playing_station(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.ui.radio.player_controller as pc

    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: False)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame)
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    controller.play_station(_station())
    controller._on_loaded(0)
    assert controller.state.state is RadioPlayerState.PLAYING
    controller.set_output_device("wasapi/{aaa}")
    assert len(fake.loads) == 2  # reconnected through the new choice


def test_device_switch_while_stopped_does_not_start_playback() -> None:
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame)
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    controller.set_output_device("wasapi/{aaa}")
    assert fake.loads == []


# -- volume boost, sound options, DVR, cross-engine rescue ----------------------


class _FakeMpvEngine(_FakeEngine):
    def __init__(self) -> None:
        super().__init__()
        self.volumes: list[int] = []
        self.filter_graphs: list[str] = []
        self.seeks: list[float] = []
        self.behind = 42.0

    def set_volume(self, percent: int) -> None:
        self.volumes.append(percent)

    def set_filter_graph(self, graph: str) -> None:
        self.filter_graphs.append(graph)

    def seek_relative(self, seconds: float) -> bool:
        self.seeks.append(seconds)
        return True

    def behind_live_seconds(self) -> float | None:
        return self.behind

    def jump_to_live(self) -> bool:
        self.seeks.append(0.0)
        return True

    def now_playing_title(self) -> str:
        return "Groove Salad - Tycho"


def _mpv_controller(monkeypatch: pytest.MonkeyPatch, **kwargs) -> tuple:
    import quill.ui.radio.player_controller as pc

    fake_mpv = _FakeMpvEngine()
    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(pc, "MpvRadioEngine", lambda *a, **k: fake_mpv)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, **kwargs)
    return controller, fake_mpv


def test_volume_boost_multiplies_on_the_mpv_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_mpv = _mpv_controller(monkeypatch)
    controller.play_station(_station())
    controller.set_volume(80)
    assert controller.set_volume_boost(True) is True
    assert fake_mpv.volumes[-1] == 120  # 80 * 1.5
    controller.set_volume_boost(False)
    assert fake_mpv.volumes[-1] == 80
    # The user-facing scale is untouched -- boost only changes the engine.
    assert controller.state.volume_percent == 80


def test_volume_boost_reports_ineffective_on_wx(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.ui.radio.player_controller as pc

    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: False)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="wx")
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    assert controller.set_volume_boost(True) is False


def test_sound_change_applies_live_on_mpv_without_reconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_mpv = _mpv_controller(monkeypatch)
    controller.play_station(_station())
    controller._on_loaded(0)
    loads_before = len(fake_mpv.loads)
    controller.set_enhancement(bass_db=6.0, mid_db=0.0, treble_db=2.0, compressor_enabled=True)
    controller.set_sound_options(channel_mode="mono", night_mode_enabled=True)
    # Heard immediately via af -- never a reconnect on the mpv engine.
    assert len(fake_mpv.loads) == loads_before
    assert "pan=mono" in fake_mpv.filter_graphs[-1]
    assert "dynaudnorm" in fake_mpv.filter_graphs[-1]
    assert "acompressor" in fake_mpv.filter_graphs[-1]


def test_dvr_rewind_and_live_route_through_the_mpv_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_mpv = _mpv_controller(monkeypatch)
    controller.play_station(_station())
    controller._on_loaded(0)
    behind = controller.rewind(30)
    assert fake_mpv.seeks[-1] == -30.0
    assert behind == 42.0
    controller.forward(15)
    assert fake_mpv.seeks[-1] == 15.0
    assert controller.jump_to_live() is True
    assert controller.engine_track_title() == "Groove Salad - Tycho"


def test_dvr_unavailable_on_wx_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.ui.radio.player_controller as pc

    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: False)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="wx")
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    controller.play_station(_station())
    controller._on_loaded(0)
    assert controller.rewind(30) is None
    assert controller.behind_live_seconds() is None
    assert controller.engine_track_title() == ""


def test_wx_error_rescued_once_by_mpv(monkeypatch: pytest.MonkeyPatch) -> None:
    # The Ogg/Opus/HLS case: WMP cannot open the stream; one silent retry
    # on the mpv engine rescues it instead of an error.
    import quill.ui.radio.player_controller as pc

    fake_mpv = _FakeMpvEngine()
    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(pc, "MpvRadioEngine", lambda *a, **k: fake_mpv)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="wx")
    fake_wx = _FakeEngine()
    controller._wx_engine = fake_wx
    controller._engine = fake_wx
    controller.play_station(_station())
    assert controller.state.state is RadioPlayerState.CONNECTING
    controller._on_error("could not open")  # WMP gives up mid-connect
    assert fake_mpv.loads  # rescued on mpv
    assert controller.state.state is RadioPlayerState.CONNECTING
    # A second failure (now on mpv, already retried) becomes a real error.
    controller._on_error("still no")
    assert controller.state.state is RadioPlayerState.ERROR


def test_error_after_playing_is_not_rescued(monkeypatch: pytest.MonkeyPatch) -> None:
    # The rescue is for "could not open", not for a drop mid-listen.
    import quill.ui.radio.player_controller as pc

    monkeypatch.setattr(pc, "mpv_output_device_available", lambda: True)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="wx")
    fake = _FakeEngine()
    controller._wx_engine = fake
    controller._engine = fake
    controller.play_station(_station())
    controller._on_loaded(0)
    controller._on_error("mid-play failure")
    assert controller.state.state is RadioPlayerState.ERROR

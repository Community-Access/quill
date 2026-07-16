"""PodcastPlayerController's Sound Enhancements wiring: routes playback
through a (fake) relay when active, seeking restarts the relay at a new
offset instead of the engine's normal instant seek, position/duration
account for the relay's own -ss offset and a probed duration, and turning
enhancements on/off mid-episode preserves play/pause intent and position.
No real ffmpeg or network -- EnhanceRelay and probe_source_duration_ms are
both faked."""

from __future__ import annotations

import pytest
import wx

import quill.ui.podcasts.player_controller as player_controller
from quill.ui.podcasts.player_controller import PodcastPlayerController

# (bass_db, mid_db, treble_db) shorthand for the old named presets.
BASS_BOOST = (7.0, 0.0, 1.0)
VOICE_CLARITY = (-3.0, 4.0, 2.0)
PODCAST = (-4.0, 3.0, 0.0)
FLAT = (0.0, 0.0, 0.0)


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _FakeEngine:
    def __init__(self) -> None:
        self._position = 0
        self.paused = True
        self.loaded_sources: list[str] = []
        self.play_count = 0
        self.pause_count = 0

    def load(self, source: str) -> bool:
        self.loaded_sources.append(source)
        self._position = 0
        return True

    def play(self) -> None:
        self.paused = False
        self.play_count += 1

    def pause(self) -> None:
        self.paused = True
        self.pause_count += 1

    def close(self) -> None:
        pass

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        self._position = ms
        if resume:
            self.play()
        elif resume is False:
            self.pause()

    def set_rate(self, _rate: float) -> None:
        pass

    def set_volume(self, _percent: int) -> None:
        pass

    def position_ms(self) -> int:
        return self._position

    def length_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return not self.paused


class _FakeRelay:
    def __init__(self) -> None:
        self.started_with: list[tuple[str, float, float, float, bool, bool, float]] = []
        self.stop_count = 0
        self._active = False

    def start(
        self,
        source: str,
        *,
        bass_db: float,
        mid_db: float,
        treble_db: float,
        compressor_enabled: bool,
        smart_speed_enabled: bool = False,
        start_seconds: float = 0.0,
    ) -> str:
        self.started_with.append((
            source,
            bass_db,
            mid_db,
            treble_db,
            compressor_enabled,
            smart_speed_enabled,
            start_seconds,
        ))
        self._active = True
        return "http://127.0.0.1:9999/enhanced.mp3"

    def stop(self) -> None:
        self.stop_count += 1
        self._active = False

    def shutdown(self) -> None:
        self.stop()

    @property
    def is_active(self) -> bool:
        return self._active


def _make_controller(
    monkeypatch: pytest.MonkeyPatch, *, probed_duration_ms: int = 60_000
) -> tuple[PodcastPlayerController, _FakeEngine, _FakeRelay]:
    monkeypatch.setattr(
        player_controller, "probe_source_duration_ms", lambda _source: probed_duration_ms
    )
    frame = wx.Frame(None)
    controller = PodcastPlayerController(frame)
    fake_engine = _FakeEngine()
    fake_relay = _FakeRelay()
    controller._engine = fake_engine  # bypass the real engine picked by create_engine
    controller._enhance_relay = fake_relay
    return controller, fake_engine, fake_relay


def _play(controller: PodcastPlayerController, fake_engine: _FakeEngine, **kwargs: object) -> None:
    controller.play_episode(
        show_id=kwargs.get("show_id", "show-1"),
        episode_guid=kwargs.get("episode_guid", "ep-1"),
        title="Title",
        source=kwargs.get("source", "https://example.com/ep.mp3"),
        resume_ms=kwargs.get("resume_ms", 0),
    )
    controller._on_loaded(0)


def _set_enhancement(
    controller: PodcastPlayerController,
    bands: tuple[float, float, float],
    *,
    compressor_enabled: bool,
    smart_speed_enabled: bool = False,
) -> None:
    bass_db, mid_db, treble_db = bands
    controller.set_enhancement(
        bass_db=bass_db,
        mid_db=mid_db,
        treble_db=treble_db,
        compressor_enabled=compressor_enabled,
        smart_speed_enabled=smart_speed_enabled,
    )


def test_unenhanced_playback_loads_the_raw_source(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _play(controller, fake_engine)
    assert fake_engine.loaded_sources == ["https://example.com/ep.mp3"]
    assert fake_relay.started_with == []


def test_enhanced_playback_loads_the_relay_url(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _set_enhancement(controller, BASS_BOOST, compressor_enabled=False)
    _play(controller, fake_engine)
    assert fake_engine.loaded_sources == ["http://127.0.0.1:9999/enhanced.mp3"]
    assert fake_relay.started_with == [
        ("https://example.com/ep.mp3", *BASS_BOOST, False, False, 0.0)
    ]


def test_enhanced_playback_reports_probed_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, _fake_relay = _make_controller(monkeypatch, probed_duration_ms=45_000)
    _set_enhancement(controller, PODCAST, compressor_enabled=True)
    _play(controller, fake_engine)
    assert controller.length_ms() == 45_000


def test_unenhanced_playback_reports_the_engines_own_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_engine, _fake_relay = _make_controller(monkeypatch)
    _play(controller, fake_engine)
    fake_engine.length_ms = lambda: 99_000  # type: ignore[method-assign]
    assert controller.length_ms() == 99_000


def test_seek_while_unenhanced_uses_the_engines_instant_seek(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _play(controller, fake_engine)
    controller.seek(30_000)
    assert fake_engine.position_ms() == 30_000
    assert fake_engine.loaded_sources == ["https://example.com/ep.mp3"]  # no reload
    assert fake_relay.started_with == []


def test_seek_while_enhanced_restarts_the_relay_at_the_new_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _set_enhancement(controller, VOICE_CLARITY, compressor_enabled=False)
    _play(controller, fake_engine)
    controller.seek(20_000)
    controller._on_loaded(0)  # simulate the reload's async completion
    assert fake_relay.started_with[-1] == (
        "https://example.com/ep.mp3",
        *VOICE_CLARITY,
        False,
        False,
        20.0,
    )
    assert controller.position_ms() == 20_000  # offset + engine's own (fresh) position 0


def test_seek_while_enhanced_and_paused_reloads_still_paused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_engine, _fake_relay = _make_controller(monkeypatch)
    _set_enhancement(controller, VOICE_CLARITY, compressor_enabled=False)
    _play(controller, fake_engine)
    controller.toggle_play_pause()  # -> paused
    assert fake_engine.paused is True
    controller.seek(10_000)
    controller._on_loaded(0)
    assert fake_engine.paused is True
    assert controller.state.state.name == "PAUSED"


def test_turning_enhancement_off_mid_episode_preserves_position_and_play_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _set_enhancement(controller, BASS_BOOST, compressor_enabled=False)
    _play(controller, fake_engine)
    fake_engine._position = 15_000  # the relay-relative engine position
    _set_enhancement(controller, FLAT, compressor_enabled=False)
    controller._on_loaded(0)
    # Went from enhanced (offset 0, engine pos 15_000 -> 15_000) to unenhanced:
    # the reload must resume-seek to that same absolute position.
    assert fake_engine.position_ms() == 15_000
    assert fake_engine.loaded_sources[-1] == "https://example.com/ep.mp3"
    assert fake_relay.stop_count >= 1


def test_stop_stops_the_relay(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _set_enhancement(controller, BASS_BOOST, compressor_enabled=False)
    _play(controller, fake_engine)
    controller.stop()
    assert fake_relay.is_active is False


def test_set_enhancement_before_anything_plays_is_remembered_not_applied_yet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _fake_engine, fake_relay = _make_controller(monkeypatch)
    _set_enhancement(controller, PODCAST, compressor_enabled=True)
    assert fake_relay.started_with == []  # nothing loaded yet, nothing to reload
    assert controller._is_enhanced() is True  # noqa: SLF001 - white-box preference check


def test_smart_speed_alone_activates_enhancement(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _set_enhancement(controller, FLAT, compressor_enabled=False, smart_speed_enabled=True)
    _play(controller, fake_engine)
    assert fake_engine.loaded_sources == ["http://127.0.0.1:9999/enhanced.mp3"]
    assert fake_relay.started_with == [("https://example.com/ep.mp3", *FLAT, False, True, 0.0)]


def test_play_episode_enhancement_kwargs_apply_per_show(monkeypatch: pytest.MonkeyPatch) -> None:
    """play_episode's own bass_db/mid_db/treble_db kwargs (resolved by the
    caller from PodcastLibrary.effective_settings) take effect without a
    separate set_enhancement call -- this is what makes different podcasts
    sound different from each other."""
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    controller.play_episode(
        show_id="show-1",
        episode_guid="ep-1",
        title="Title",
        source="https://example.com/ep.mp3",
        bass_db=PODCAST[0],
        mid_db=PODCAST[1],
        treble_db=PODCAST[2],
        compressor_enabled=True,
    )
    controller._on_loaded(0)
    assert fake_engine.loaded_sources == ["http://127.0.0.1:9999/enhanced.mp3"]
    assert fake_relay.started_with == [("https://example.com/ep.mp3", *PODCAST, True, False, 0.0)]

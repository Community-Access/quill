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
        self.started_with: list[tuple[str, str, bool, float]] = []
        self.stop_count = 0
        self._active = False

    def start(
        self, source: str, *, eq_preset: str, compressor_enabled: bool, start_seconds: float = 0.0
    ) -> str:
        self.started_with.append((source, eq_preset, compressor_enabled, start_seconds))
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


def test_unenhanced_playback_loads_the_raw_source(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    _play(controller, fake_engine)
    assert fake_engine.loaded_sources == ["https://example.com/ep.mp3"]
    assert fake_relay.started_with == []


def test_enhanced_playback_loads_the_relay_url(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    controller.set_enhancement("Bass Boost", compressor_enabled=False)
    _play(controller, fake_engine)
    assert fake_engine.loaded_sources == ["http://127.0.0.1:9999/enhanced.mp3"]
    assert fake_relay.started_with == [("https://example.com/ep.mp3", "Bass Boost", False, 0.0)]


def test_enhanced_playback_reports_probed_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, _fake_relay = _make_controller(monkeypatch, probed_duration_ms=45_000)
    controller.set_enhancement("Podcast", compressor_enabled=True)
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
    controller.set_enhancement("Voice Clarity", compressor_enabled=False)
    _play(controller, fake_engine)
    controller.seek(20_000)
    controller._on_loaded(0)  # simulate the reload's async completion
    assert fake_relay.started_with[-1] == (
        "https://example.com/ep.mp3",
        "Voice Clarity",
        False,
        20.0,
    )
    assert controller.position_ms() == 20_000  # offset + engine's own (fresh) position 0


def test_seek_while_enhanced_and_paused_reloads_still_paused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, fake_engine, _fake_relay = _make_controller(monkeypatch)
    controller.set_enhancement("Voice Clarity", compressor_enabled=False)
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
    controller.set_enhancement("Bass Boost", compressor_enabled=False)
    _play(controller, fake_engine)
    fake_engine._position = 15_000  # the relay-relative engine position
    controller.set_enhancement("Flat", compressor_enabled=False)
    controller._on_loaded(0)
    # Went from enhanced (offset 0, engine pos 15_000 -> 15_000) to unenhanced:
    # the reload must resume-seek to that same absolute position.
    assert fake_engine.position_ms() == 15_000
    assert fake_engine.loaded_sources[-1] == "https://example.com/ep.mp3"
    assert fake_relay.stop_count >= 1


def test_stop_stops_the_relay(monkeypatch: pytest.MonkeyPatch) -> None:
    controller, fake_engine, fake_relay = _make_controller(monkeypatch)
    controller.set_enhancement("Bass Boost", compressor_enabled=False)
    _play(controller, fake_engine)
    controller.stop()
    assert fake_relay.is_active is False


def test_set_enhancement_before_anything_plays_is_remembered_not_applied_yet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller, _fake_engine, fake_relay = _make_controller(monkeypatch)
    controller.set_enhancement("Podcast", compressor_enabled=True)
    assert fake_relay.started_with == []  # nothing loaded yet, nothing to reload
    assert controller._is_enhanced() is True  # noqa: SLF001 - white-box preference check

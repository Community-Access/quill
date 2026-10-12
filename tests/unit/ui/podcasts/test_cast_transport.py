"""Global transport feedback describes accepted audio actions, not assumed ones."""

from __future__ import annotations

import ctypes
from types import SimpleNamespace

import pytest

from quill.ui.audio.audio_engine import WxMediaEngine
from quill.ui.audio.mpv_engine import MpvAudioEngine, _MpvClient
from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin
from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.podcasts.player_controller import (
    PodcastPlaybackState,
    PodcastPlayerController,
    PodcastPlayerState,
)


class Engine:
    def __init__(self):
        self.playing = True
        self.calls = []
        self.reject = False

    def play(self):
        self.calls.append("play")
        if self.reject:
            raise OSError("synthetic refusal")
        self.playing = True

    def pause(self):
        self.calls.append("pause")
        if self.reject:
            raise OSError("synthetic refusal")
        self.playing = False

    def position_ms(self):
        return 42_000

    def set_rate(self, _rate):
        pass

    def seek(self, _ms, *, resume):
        self.play() if resume else self.pause()


def _controller(state=PodcastPlayerState.PLAYING):
    controller = object.__new__(PodcastPlayerController)
    controller._state = PodcastPlaybackState(state, "show", "episode", "Synthetic title")
    controller._engine = Engine()
    controller._pending_play_after_load = True
    controller._resume_ms = 0
    controller._pending_rate = 1.0
    controller._enhanced_source = "synthetic"
    controller._on_state_changed = None
    controller._on_position_checkpoint = lambda *_args: controller._engine.calls.append(
        "checkpoint"
    )
    controller._is_enhanced = lambda: False
    return controller


def test_pause_reaches_the_engine_before_position_bookkeeping():
    controller = _controller()

    controller.toggle_play_pause()

    assert controller._engine.calls == ["pause", "checkpoint"]
    assert controller.state.state is PodcastPlayerState.PAUSED
    assert controller._engine.playing is False


@pytest.mark.parametrize("state", [PodcastPlayerState.PLAYING, PodcastPlayerState.PAUSED])
def test_refused_transport_does_not_announce_a_successful_state_change(state):
    controller = _controller(state)
    controller._engine.reject = True
    spoken = []
    host = SimpleNamespace(_podcast_controller=controller, _announce=spoken.append)

    PodcastsMixin.podcast_toggle_play_pause(host)

    assert controller.state.state is PodcastPlayerState.ERROR
    assert "could not" in spoken[-1]
    assert "Podcasts: paused" not in spoken[-1]
    assert "Podcasts: playing" not in spoken[-1]


def test_a_press_while_loading_sets_the_actual_pending_pause_intent():
    controller = _controller(PodcastPlayerState.LOADING)

    controller.toggle_play_pause()

    assert controller._pending_play_after_load is False
    assert "remain paused" in controller.state.status_text
    controller._on_loaded(100_000)
    assert controller._engine.playing is False
    assert controller.state.state is PodcastPlayerState.PAUSED
    controller.toggle_play_pause()
    assert controller.state.state is PodcastPlayerState.PLAYING
    assert controller._engine.playing is True


def test_repeated_presses_while_loading_coalesce_to_the_latest_intent():
    controller = _controller(PodcastPlayerState.LOADING)

    controller.toggle_play_pause()
    controller.toggle_play_pause()
    controller._on_loaded(100_000)

    assert controller._engine.calls == ["play"]
    assert controller.state.state is PodcastPlayerState.PLAYING


def test_load_completion_cannot_overwrite_a_transport_refusal():
    controller = _controller(PodcastPlayerState.LOADING)
    controller._engine.reject = True

    controller._on_loaded(100_000)

    assert controller.state.state is PodcastPlayerState.ERROR


def test_a_late_load_callback_cannot_restart_a_stopped_player():
    controller = _controller(PodcastPlayerState.STOPPED)

    controller._on_loaded(100_000)

    assert controller._engine.calls == []
    assert controller.state.state is PodcastPlayerState.STOPPED


def test_synchronous_backend_error_is_not_overwritten_by_transport_feedback():
    controller = _controller()
    controller._engine.pause = lambda: controller._set_state(
        PodcastPlayerState.ERROR, message="Synthetic backend failure"
    )

    controller.toggle_play_pause()

    assert controller.state.state is PodcastPlayerState.ERROR


def test_a_background_global_press_changes_audio_without_restoring_the_window():
    controller = _controller()
    restored = []

    class Host(GlobalHotkeysMixin, PodcastsMixin):
        pass

    host = Host()
    host._podcast_controller = controller
    host._global_hotkey_map = {42: "podcasts.play_pause"}
    host._restore_from_tray = lambda: restored.append(True)
    spoken = []
    host._announce = spoken.append
    host.commands = SimpleNamespace(run=lambda _command: host.podcast_toggle_play_pause())
    event = SimpleNamespace(GetId=lambda: 42)

    host._on_global_hotkey(event)
    assert controller._engine.playing is False
    host._on_global_hotkey(event)
    assert controller._engine.playing is True
    assert restored == []
    assert spoken[-1].startswith("Podcasts: playing")


@pytest.mark.parametrize("operation", ["play", "pause"])
def test_windows_media_false_return_is_a_transport_error(operation):
    engine = object.__new__(WxMediaEngine)
    engine._loaded = True
    engine._media = SimpleNamespace(Play=lambda: False, Pause=lambda: False)

    with pytest.raises(OSError, match="Windows Media"):
        getattr(engine, operation)()


@pytest.mark.parametrize("operation", ["play", "pause"])
def test_mpv_negative_property_status_is_a_transport_error(operation):
    engine = object.__new__(MpvAudioEngine)
    engine._loaded = True
    engine._mpv = SimpleNamespace(set_str=lambda *_args: -3)

    with pytest.raises(OSError, match="rejected"):
        getattr(engine, operation)()


def test_mpv_command_failure_is_not_ignored():
    client = object.__new__(_MpvClient)
    client._handle = ctypes.c_void_p(1)
    client._lib = SimpleNamespace(mpv_command=lambda *_args: -2)

    with pytest.raises(OSError, match="status -2"):
        client.command("pause")


@pytest.mark.parametrize("operation", ["get_double", "get_flag", "get_str"])
def test_a_terminated_client_never_passes_a_null_handle_to_native_code(operation):
    client = object.__new__(_MpvClient)
    client._handle = ctypes.c_void_p(None)

    with pytest.raises(OSError, match="no longer available"):
        getattr(client, operation)("duration")


def test_a_queued_poll_cannot_touch_a_terminated_native_client():
    engine = object.__new__(MpvAudioEngine)
    engine._terminated = True

    engine._on_poll(None)


def test_shutdown_releases_inactive_stream_engine_and_survives_checkpoint_failure():
    controller = _controller()
    calls = []
    controller._on_position_checkpoint = lambda *_args: (_ for _ in ()).throw(OSError("test"))
    active = SimpleNamespace(
        close=lambda: calls.append("active-close"),
        terminate=lambda: calls.append("active-terminate"),
        position_ms=lambda: 42_000,
    )
    controller._engine = controller._spotify_engine = active
    controller._stream_engine = SimpleNamespace(
        close=lambda: calls.append("stream-close"),
        terminate=lambda: calls.append("stream-terminate"),
    )
    controller._enhance_relay = SimpleNamespace(shutdown=lambda: calls.append("relay"))
    controller._outro_poll_timer = SimpleNamespace(Stop=lambda: calls.append("timer"))

    controller.shutdown()
    controller.shutdown()

    assert calls == [
        "active-close",
        "active-terminate",
        "stream-close",
        "stream-terminate",
        "relay",
        "timer",
    ]


def test_a_late_load_callback_cannot_touch_a_closed_player():
    controller = _controller(PodcastPlayerState.LOADING)
    controller._closed = True

    controller._on_loaded(100_000)
    controller.toggle_play_pause()

    assert controller._engine.calls == []


def test_stopping_mpv_keeps_the_native_client_reusable_until_parent_destruction():
    calls = []
    engine = object.__new__(MpvAudioEngine)
    engine._loaded = True
    engine._terminated = False
    engine._timer = SimpleNamespace(Stop=lambda: calls.append("timer"))
    engine._mpv = SimpleNamespace(
        command=lambda *args: calls.append(args),
        close=lambda: calls.append("destroy"),
    )

    engine.close()
    assert ("stop",) in calls
    assert "destroy" not in calls
    engine.terminate()
    engine.terminate()
    assert calls.count("destroy") == 1

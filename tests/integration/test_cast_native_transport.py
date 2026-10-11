"""Muted real-media acceptance for Cast's background global transport route."""

from __future__ import annotations

import ctypes
import os
import sys
import wave
from ctypes import wintypes
from time import monotonic, sleep

import pytest

pytestmark = [
    pytest.mark.machine_global,
    pytest.mark.skipif(
        sys.platform != "win32" or os.environ.get("QUILL_NATIVE_MEDIA_TESTS") != "1",
        reason="Requires opt-in Windows audio-engine acceptance",
    ),
]


@pytest.mark.parametrize("backend", ["windows", "mpv"])
def test_background_pause_resume_and_stop_reload_change_native_playback(
    backend, tmp_path, monkeypatch
):
    import wx

    from quill.core.commands import CommandRegistry
    from quill.ui.audio.audio_engine import create_windows_engine
    from quill.ui.audio.mpv_engine import MpvAudioEngine, find_libmpv
    from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin
    from quill.ui.main_frame_podcasts import PodcastsMixin
    from quill.ui.podcasts import player_controller
    from quill.ui.podcasts.player_controller import PodcastPlayerController, PodcastPlayerState

    if backend == "mpv" and find_libmpv() is None:
        pytest.skip("Optional mpv engine is not installed")
    source = tmp_path / "synthetic-muted.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * 16_000 * 20)

    factory = MpvAudioEngine if backend == "mpv" else create_windows_engine
    monkeypatch.setattr(player_controller, "create_engine", factory)
    app = wx.GetApp() or wx.App()
    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    frame = wx.Frame(None, title="Muted Cast transport acceptance")
    controller = None
    registered = False
    hotkey_reference = wx.NewIdRef()
    hotkey_id = int(hotkey_reference)
    spoken = []

    def pump():
        app.ProcessPendingEvents()
        wx.YieldIfNeeded()
        loop.ProcessIdle()
        sleep(0.005)

    def until(predicate, seconds=12):
        deadline = monotonic() + seconds
        while not predicate() and monotonic() < deadline:
            pump()
        assert predicate(), (controller.state.status_text, spoken)

    def post_hotkey():
        post = ctypes.windll.user32.PostMessageW
        post.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        post.restype = wintypes.BOOL
        assert post(frame.GetHandle(), 0x0312, hotkey_id, (0x84 << 16) | 0x07)

    try:
        controller = PodcastPlayerController(frame)
        controller.set_volume(0)

        class Host(GlobalHotkeysMixin, PodcastsMixin):
            pass

        host = Host()
        host._podcast_controller = controller
        host._global_hotkey_map = {hotkey_id: "podcasts.play_pause"}
        host._announce = spoken.append
        host.commands = CommandRegistry()
        host.commands.register("podcasts.play_pause", "Play/Pause", host.podcast_toggle_play_pause)
        frame.Bind(wx.EVT_HOTKEY, host._on_global_hotkey)
        registered = frame.RegisterHotKey(
            hotkey_id, wx.MOD_CONTROL | wx.MOD_ALT | wx.MOD_SHIFT, wx.WXK_F21
        )
        assert registered, "The isolated F21 test hotkey could not be registered"
        assert not frame.IsShown()

        def start(guid):
            controller.play_episode(
                show_id="synthetic",
                episode_guid=guid,
                title="Synthetic muted acceptance audio",
                source=str(source),
            )

        start("first")
        until(
            lambda: (
                controller.state.state is PodcastPlayerState.PLAYING
                and controller.position_ms() >= 300
            )
        )
        engine = controller._engine
        post_hotkey()
        until(lambda: controller.state.state is PodcastPlayerState.PAUSED)
        paused_position = controller.position_ms()
        deadline = monotonic() + 0.6
        while monotonic() < deadline:
            pump()
        assert abs(controller.position_ms() - paused_position) <= 80
        assert not controller.is_playing()

        post_hotkey()
        until(
            lambda: (
                controller.state.state is PodcastPlayerState.PLAYING
                and controller.position_ms() >= paused_position + 250
            )
        )
        announcements_before = len(spoken)
        for _index in range(4):
            post_hotkey()
        until(lambda: len(spoken) == announcements_before + 4)
        assert controller.state.state is PodcastPlayerState.PLAYING
        resumed_position = controller.position_ms()
        until(lambda: controller.position_ms() >= resumed_position + 200)

        controller.stop()
        assert controller.state.state is PodcastPlayerState.STOPPED
        start("second")
        until(
            lambda: (
                controller.state.state is PodcastPlayerState.PLAYING
                and controller.position_ms() >= 300
            )
        )
        assert controller._engine is engine
        assert controller.is_playing()
        assert not frame.IsShown()
        print(
            f"{backend}: native {type(engine).__name__}; background pause/resume, "
            "four rapid global presses, and Stop -> Play reuse passed"
        )
    finally:
        if registered:
            frame.UnregisterHotKey(hotkey_id)
        if controller is not None:
            controller.shutdown()
        frame.Destroy()
        app.ProcessPendingEvents()
        wx.EventLoop.SetActive(previous_loop)

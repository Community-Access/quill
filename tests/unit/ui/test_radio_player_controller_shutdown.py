"""#1195: on the real exit path, an engine that keeps a live handle after
close() (mpv) must be hard-terminated so audio never outlives the app."""

from __future__ import annotations

import pytest
import wx

from quill.ui.radio.player_controller import RadioPlayerController


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _EngineWithTerminate:
    def __init__(self) -> None:
        self.closed = False
        self.terminated = False

    def close(self) -> None:
        self.closed = True

    def terminate(self) -> None:
        self.terminated = True


class _EngineWithoutTerminate:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _controller(engine) -> RadioPlayerController:
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="wx")
    controller._wx_engine = engine
    controller._engine = engine
    return controller


def test_shutdown_hard_terminates_engine_that_supports_it() -> None:
    engine = _EngineWithTerminate()
    _controller(engine).shutdown()
    assert engine.closed is True
    assert engine.terminated is True


def test_shutdown_is_safe_for_engines_without_terminate() -> None:
    engine = _EngineWithoutTerminate()
    # Must not raise for the classic WMP engine, which has no terminate().
    _controller(engine).shutdown()
    assert engine.closed is True

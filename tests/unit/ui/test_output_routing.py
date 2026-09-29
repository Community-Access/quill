"""One device list and one "can this machine route?" for every engine (2026-09-29)."""

from __future__ import annotations

import pytest

from quill.ui.audio import audio_engine, output_routing, winrt_engine
from quill.ui.radio import mpv_radio_engine

MPV_LIST = [("wasapi/{aaaa0000-0000-0000-0000-000000000001}", "Speakers (mpv saw it)")]
WINDOWS_LIST = [("wasapi/{aaaa0000-0000-0000-0000-000000000001}", "Speakers (Windows saw it)")]


def test_mpv_enumerates_when_it_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mpv_radio_engine, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(mpv_radio_engine, "list_audio_devices", lambda: list(MPV_LIST))
    monkeypatch.setattr(winrt_engine, "list_audio_devices", lambda: list(WINDOWS_LIST))
    assert output_routing.list_output_devices() == MPV_LIST


def test_windows_enumerates_when_mpv_is_absent_or_answers_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(winrt_engine, "list_audio_devices", lambda: list(WINDOWS_LIST))
    monkeypatch.setattr(mpv_radio_engine, "mpv_output_device_available", lambda: False)
    monkeypatch.setattr(mpv_radio_engine, "list_audio_devices", lambda: list(MPV_LIST))
    assert output_routing.list_output_devices() == WINDOWS_LIST
    monkeypatch.setattr(mpv_radio_engine, "mpv_output_device_available", lambda: True)
    monkeypatch.setattr(mpv_radio_engine, "list_audio_devices", lambda: [])
    assert output_routing.list_output_devices() == WINDOWS_LIST


def test_routing_is_available_with_either_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mpv_radio_engine, "mpv_output_device_available", lambda: False)
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: False)
    assert output_routing.output_device_routing_available() is False
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: True)
    assert output_routing.output_device_routing_available() is True
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: False)
    monkeypatch.setattr(mpv_radio_engine, "mpv_output_device_available", lambda: True)
    assert output_routing.output_device_routing_available() is True


@pytest.fixture(scope="module")
def wx_app():
    import wx

    app = wx.App()
    yield app
    app.Destroy()


def test_the_windows_engine_factory_falls_to_the_classic_control(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the projection, create_windows_engine is the wx.media control;
    with a projection that fails to build, likewise -- the classic control is
    the floor and the factory never raises."""
    import wx

    frame = wx.Frame(None)
    try:
        monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: False)
        engine = audio_engine.create_windows_engine(
            frame, on_loaded=lambda _ms: None, on_finished=lambda: None, on_error=lambda _m: None
        )
        assert isinstance(engine, audio_engine.WxMediaEngine)

        class _Broken:
            def __init__(self, *_a: object, **_k: object) -> None:
                raise RuntimeError("MediaPlayer activation failed")

        monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: True)
        monkeypatch.setattr(winrt_engine, "WinRtMediaEngine", _Broken)
        engine = audio_engine.create_windows_engine(
            frame, on_loaded=lambda _ms: None, on_finished=lambda: None, on_error=lambda _m: None
        )
        assert isinstance(engine, audio_engine.WxMediaEngine)
    finally:
        frame.Destroy()


def test_create_engine_prefers_the_windows_engine_over_the_classic_control(
    wx_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cast, Player, Studio and Beacon build through create_engine: with no
    libmpv, the modern Windows engine comes before the classic control."""
    import wx

    frame = wx.Frame(None)
    built: list[str] = []

    class _Modern:
        def __init__(self, *_a: object, **_k: object) -> None:
            built.append("modern")

    try:
        monkeypatch.setattr(audio_engine, "preferred_backend", lambda: "wx")
        monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: True)
        monkeypatch.setattr(winrt_engine, "WinRtMediaEngine", _Modern)
        engine = audio_engine.create_engine(
            frame, on_loaded=lambda _ms: None, on_finished=lambda: None, on_error=lambda _m: None
        )
        assert isinstance(engine, _Modern)
        assert built == ["modern"]
    finally:
        frame.Destroy()

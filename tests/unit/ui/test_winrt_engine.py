"""The modern Windows Media engine (2026-09-29): the pure parts everywhere, the
real player where Windows offers it.

The real-player tests play the corpus MP3 for under two seconds on the
machine's sound card, so they share the ``machine_global`` worker, and they
are skipped wherever the pywinrt projection is absent (CI without the
``windows-media`` extra, non-Windows). Events from ``MediaPlayer`` arrive
only while a real wx main loop runs -- ``Yield`` pumping does not deliver
them (probed 2026-09-29) -- so the helper below drives ``MainLoop`` with a
``CallLater`` poll.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from quill.ui.audio import winrt_engine

CORPUS_MP3 = Path(__file__).resolve().parents[2] / "corpus" / "audio" / "chaptered-sample.mp3"
HEADSET = "wasapi/{ca86f65f-6b12-449a-ae6d-e99036afdb13}"

# -- pure ---------------------------------------------------------------------------


def test_device_guid_reads_mpvs_naming_and_nothing_else() -> None:
    assert winrt_engine.device_guid(HEADSET) == "ca86f65f-6b12-449a-ae6d-e99036afdb13"
    assert winrt_engine.device_guid("WASAPI/{CA86F65F-6B12-449A-AE6D-E99036AFDB13}") == (
        "ca86f65f-6b12-449a-ae6d-e99036afdb13"
    )
    assert winrt_engine.device_guid("") == ""
    assert winrt_engine.device_guid("auto") == ""
    assert winrt_engine.device_guid("Speakers (Realtek)") == ""


def test_endpoint_ids_carry_the_same_guid_mpv_names() -> None:
    """Windows' endpoint id and libmpv's device name agree on the GUID, which is
    what lets one saved setting serve both engines."""
    endpoint = (
        "\\\\?\\SWD#MMDEVAPI#{0.0.0.00000000}.{ca86f65f-6b12-449a-ae6d-e99036afdb13}"
        "#{e6327cad-dcec-4949-ae8a-991e976a79d2}"
    )
    match = winrt_engine._ENDPOINT_GUID.search(endpoint)
    assert match is not None
    assert f"wasapi/{{{match.group(1)}}}" == HEADSET


def test_no_projection_means_no_devices_and_no_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: False)
    assert winrt_engine.list_audio_devices() == []
    with pytest.raises(OSError):
        winrt_engine.WinRtMediaEngine(
            None, on_loaded=lambda _ms: None, on_finished=lambda: None, on_error=lambda _m: None
        )


def test_a_failed_enumeration_is_an_empty_list_not_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: True)

    def broken() -> list[Any]:
        raise RuntimeError("no MMDevice")

    monkeypatch.setattr(winrt_engine, "_enumerate", broken)
    assert winrt_engine.list_audio_devices() == []


def test_local_paths_are_told_from_addresses() -> None:
    assert winrt_engine._looks_like_local_path("C:\\Music\\a.mp3")
    assert winrt_engine._looks_like_local_path("S:/QUILL/x.mp3")
    assert winrt_engine._looks_like_local_path("\\\\server\\share\\a.mp3")
    assert not winrt_engine._looks_like_local_path("https://ice1.somafm.com/groovesalad-128-mp3")
    assert not winrt_engine._looks_like_local_path("http://127.0.0.1:8123/relay")


# -- the real player ----------------------------------------------------------------

needs_engine = pytest.mark.skipif(
    not winrt_engine.winrt_media_available(), reason="the pywinrt media projection is absent"
)


@pytest.fixture(scope="module")
def wx_app():
    import wx

    app = wx.App()
    yield app
    app.Destroy()


def _run_until(app: Any, done: Any, timeout: float) -> None:
    """Drive the main loop until ``done()`` or *timeout* seconds."""
    import wx

    deadline = time.monotonic() + timeout

    def poll() -> None:
        if done() or time.monotonic() > deadline:
            app.ExitMainLoop()
        else:
            wx.CallLater(25, poll)

    wx.CallLater(25, poll)
    app.MainLoop()


@pytest.mark.machine_global
@needs_engine
def test_a_local_file_opens_with_its_length_seeks_and_plays(wx_app) -> None:
    import wx

    frame = wx.Frame(None)
    got: dict[str, Any] = {}
    engine = winrt_engine.WinRtMediaEngine(
        frame,
        on_loaded=lambda ms: got.setdefault("loaded", ms),
        on_finished=lambda: got.setdefault("finished", True),
        on_error=lambda m: got.setdefault("error", m),
    )
    try:
        engine.set_volume(0)  # heard by nobody; the device is still opened
        assert engine.load(str(CORPUS_MP3)) is True
        _run_until(wx_app, lambda: bool(got), 8)
        assert "error" not in got, got
        assert got["loaded"] > 200_000  # a four-minute file, in milliseconds
        assert engine.length_ms() == got["loaded"]
        engine.play()
        _run_until(wx_app, lambda: engine.position_ms() > 200, 5)
        assert engine.is_playing()
        engine.seek(60_000, resume=False)
        _run_until(wx_app, lambda: engine.position_ms() >= 59_000, 3)
        assert 59_000 <= engine.position_ms() <= 62_000
        assert not engine.is_playing()
    finally:
        engine.terminate()
        frame.Destroy()


@pytest.mark.machine_global
@needs_engine
def test_an_address_that_will_not_open_reports_an_error_once(wx_app) -> None:
    import wx

    frame = wx.Frame(None)
    errors: list[str] = []
    engine = winrt_engine.WinRtMediaEngine(
        frame,
        on_loaded=lambda _ms: errors.append("loaded?!"),
        on_finished=lambda: None,
        on_error=errors.append,
    )
    try:
        assert engine.load("https://127.0.0.1:9/nothing.mp3") is True
        _run_until(wx_app, lambda: bool(errors), 10)
        assert len(errors) == 1
        assert errors[0].startswith("Windows Media could not play this stream")
        assert not engine.is_playing()
    finally:
        engine.terminate()
        frame.Destroy()


@pytest.mark.machine_global
@needs_engine
def test_a_superseded_load_never_reports(wx_app) -> None:
    """Two loads back to back: only the second one's verdict arrives."""
    import wx

    frame = wx.Frame(None)
    got: list[str] = []
    engine = winrt_engine.WinRtMediaEngine(
        frame,
        on_loaded=lambda _ms: got.append("loaded"),
        on_finished=lambda: None,
        on_error=lambda m: got.append(f"error {m}"),
    )
    try:
        engine.set_volume(0)
        engine.load(str(CORPUS_MP3))
        engine.load(str(CORPUS_MP3))
        _run_until(wx_app, lambda: bool(got), 8)
        _run_until(wx_app, lambda: False, 0.5)  # give a stale one time to show up
        assert got == ["loaded"]
    finally:
        engine.terminate()
        frame.Destroy()


@pytest.mark.machine_global
@needs_engine
def test_the_device_switches_live_and_a_name_windows_lacks_is_ignored(wx_app, caplog) -> None:
    import logging

    import wx

    devices = winrt_engine.list_audio_devices()
    if not devices:
        pytest.skip("no audio render device on this machine")
    assert all(name.startswith("wasapi/{") for name, _ in devices)
    frame = wx.Frame(None)
    got: dict[str, Any] = {}
    engine = winrt_engine.WinRtMediaEngine(
        frame,
        on_loaded=lambda ms: got.setdefault("loaded", ms),
        on_finished=lambda: None,
        on_error=lambda m: got.setdefault("error", m),
        audio_device=devices[-1][0],
    )
    try:
        assert engine.audio_device == devices[-1][0]
        engine.set_volume(0)
        engine.load(str(CORPUS_MP3))
        _run_until(wx_app, lambda: bool(got), 8)
        engine.play()
        _run_until(wx_app, lambda: engine.position_ms() > 200, 5)
        engine.set_audio_device(devices[0][0])
        _run_until(wx_app, lambda: False, 0.5)
        assert engine.audio_device == devices[0][0]
        assert engine.is_playing()  # the switch did not stop the sound
        with caplog.at_level(logging.WARNING, logger="quill.ui.audio.winrt_engine"):
            engine.set_audio_device("wasapi/{00000000-0000-0000-0000-000000000000}")
        assert engine.audio_device == devices[0][0]  # kept the previous one
        assert any("no device named" in r.message for r in caplog.records)
        engine.set_audio_device("")
        assert engine.audio_device == ""
    finally:
        engine.terminate()
        frame.Destroy()

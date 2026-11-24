"""FUX-11: Test These Settings in Radio's Recording Settings.

The test records with the choices in the window now, through the real
command, into a temporary folder; it says what an hour weighs, labels itself
out of date when a choice changes, and leaves the recordings folder alone.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.radio.recording import RecordingSettings  # noqa: E402
from quill.ui.radio import recording_settings_dialog as rsd  # noqa: E402
from quill.ui.radio import test_recording_controls as trc  # noqa: E402


def _host(tmp_path: Path, *, playing: bool = True) -> SimpleNamespace:
    station = SimpleNamespace(name="WXYZ", stream_url="http://example.test/s", is_recording=False)
    host = SimpleNamespace(
        frame=None,
        said=[],
        _radio_controller=SimpleNamespace(
            state=SimpleNamespace(station=station if playing else None)
        ),
        _radio_recording_settings=RecordingSettings(
            destination_root=str(tmp_path / "recordings"), apply_sound_enhancements=False
        ),
    )
    host._announce = host.said.append
    host._radio_recording_filter_graph = lambda: (
        "eq" if host._radio_recording_settings.apply_sound_enhancements else ""
    )
    return host


class _Thread:
    def __init__(self, *, target: Any, daemon: bool, name: str) -> None:
        assert daemon
        self.target = target

    def start(self) -> None:
        self.target()


def _dialog(host: Any) -> Any:
    return rsd.RecordingSettingsDialog(
        None, settings=host._radio_recording_settings, announce_cb=host._announce, host=host
    )


def test_the_box_says_what_an_hour_weighs_and_follows_the_choice(
    wx_session_app: Any, tmp_path: Path
) -> None:
    dlg = _dialog(_host(tmp_path))
    try:
        assert "An hour at 192 kbps is about" in dlg.test.result.GetValue()
        dlg._bitrate_choice.SetSelection(rsd._BITRATE_CHOICES.index(96))
        dlg.test.refresh()
        assert "An hour at 96 kbps" in dlg.test.result.GetValue()
    finally:
        dlg.dialog.Destroy()


def test_a_test_records_with_the_window_choices_into_a_temporary_folder(
    wx_session_app: Any, wx_call_after: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import http_client
    from quill.core.radio import recording
    from quill.core.speech import ffmpeg as ffmpeg_mod

    monkeypatch.setattr(trc.threading, "Thread", _Thread)
    monkeypatch.setattr(ffmpeg_mod, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(recording, "_resolve_capture_url", lambda url: url)
    monkeypatch.setattr(http_client, "user_agent", lambda: "QUILL")
    monkeypatch.setattr(trc, "_seconds_of", lambda _p: 30.0)
    runs: list[list[str]] = []

    def fake_run(args: list[str], stop: Any) -> float:
        runs.append(args)
        Path(args[-1]).write_bytes(b"x" * 720_000)
        return 30.0

    monkeypatch.setattr(trc, "run_test", fake_run)
    wx_call_after()
    host = _host(tmp_path)
    dlg = _dialog(host)
    try:
        dlg._apply_enhancements_check.SetValue(True)  # not saved: the test follows the window
        dlg.test.press()
        args = runs[0]
        assert "eq" in " ".join(args)  # the window's Sound Enhancements choice
        out = Path(args[-1])
        assert not out.is_relative_to(tmp_path / "recordings")
        text = dlg.test.result.GetValue()
        assert "30 seconds made" in text and "so an hour should be about 82.4 MB" in text
        assert dlg.test.hear_button.IsEnabled()
        assert host.said[-1].startswith("Test recording done")
        assert host._radio_recording_settings.apply_sound_enhancements is False  # restored

        dlg._format_choice.SetSelection(2)  # FLAC
        dlg.test.refresh()
        assert "Out of date:" in dlg.test.result.GetValue()
        assert host.said[-1] == "Test result is out of date."
        said = len(host.said)
        dlg.test.refresh()  # said once, not on every change
        assert len(host.said) == said
        folder = out.parent
        dlg.test.close()
        assert not folder.exists()
    finally:
        dlg.dialog.Destroy()


def test_no_station_playing_says_so_and_records_nothing(
    wx_session_app: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs: list[Any] = []
    monkeypatch.setattr(trc, "run_test", lambda *a: runs.append(a))
    host = _host(tmp_path, playing=False)
    dlg = _dialog(host)
    try:
        dlg.test.press()
        assert runs == [] and "Play a live station first" in host.said[-1]
        assert "Play a live station first" in dlg.test.result.GetValue()  # kept as text
        dlg.test.hear()
        assert "Nothing to hear yet" in host.said[-1]
    finally:
        dlg.dialog.Destroy()


def test_stop_drops_the_late_result(
    wx_session_app: Any, wx_call_after: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import http_client
    from quill.core.radio import recording
    from quill.core.speech import ffmpeg as ffmpeg_mod

    started: list[Any] = []

    class _Later(_Thread):
        def start(self) -> None:
            started.append(self.target)

    monkeypatch.setattr(trc.threading, "Thread", _Later)
    monkeypatch.setattr(ffmpeg_mod, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(recording, "_resolve_capture_url", lambda url: url)
    monkeypatch.setattr(http_client, "user_agent", lambda: "QUILL")
    monkeypatch.setattr(trc, "run_test", lambda args, stop: 3.0)
    wx_call_after()
    host = _host(tmp_path)
    dlg = _dialog(host)
    try:
        dlg.test.press()
        assert dlg.test.running and "Stop" in dlg.test.test_button.GetLabel()
        dlg.test.press()
        assert not dlg.test.running
        started[0]()
        assert "so an hour should be" not in dlg.test.result.GetValue()
    finally:
        dlg.dialog.Destroy()


def test_open_recording_settings_saves_what_ok_chose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved: list[Any] = []
    chosen = replace(RecordingSettings(), bitrate_kbps=320)

    class _Dialog:
        def __init__(self, *_a: Any, host: Any = None, **_k: Any) -> None:
            assert host is not None  # the test needs the playing station

        def show(self) -> Any:
            return chosen

    from quill.core.radio import recording

    monkeypatch.setattr(rsd, "RecordingSettingsDialog", _Dialog)
    monkeypatch.setattr(recording, "save_recording_settings", lambda d, s: saved.append(s))
    host = _host(tmp_path)
    host._radio_scheduler = SimpleNamespace(set_recording_settings=lambda s: saved.append(s))
    rsd.open_recording_settings(host)
    assert host._radio_recording_settings is chosen
    assert saved == [chosen, chosen]
    assert host.said[-1] == "Recording settings saved"

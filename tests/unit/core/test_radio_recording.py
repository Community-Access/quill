"""Tests for radio stream recording: filename building, command building, and
the recorder's start/stop lifecycle (no real ffmpeg or network)."""

from __future__ import annotations

import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

import quill.core.radio.recording as recording
from quill.core.radio.recording import (
    RadioRecorder,
    RecordingError,
    RecordingSettings,
    build_filename,
    build_record_command,
    load_recording_settings,
    save_recording_settings,
)


def test_settings_to_dict_from_dict_round_trip() -> None:
    original = RecordingSettings(
        format="ogg",
        bitrate_kbps=256,
        destination_root="D:/recordings",
        filename_pattern="{station}_{date}",
        max_duration_minutes=45,
    )
    restored = RecordingSettings.from_dict(original.to_dict())
    assert restored == original


def test_settings_from_dict_defaults_and_rejects_unknown_format() -> None:
    settings = RecordingSettings.from_dict({"format": "wma"})
    assert settings.format == "mp3"
    settings = RecordingSettings.from_dict({})
    assert settings.max_duration_minutes == 180


def test_build_filename_fills_tokens_and_sanitizes() -> None:
    when = datetime(2026, 7, 14, 8, 30, 0)
    name = build_filename("{station}: Live/Show? {date} {time}", station="WXYZ", when=when)
    assert name == "WXYZ LiveShow 2026-07-14 08-30-00"


def test_build_filename_falls_back_when_sanitized_to_empty() -> None:
    when = datetime(2026, 7, 14, 8, 30, 0)
    assert build_filename("???", station="", when=when) == "recording"


def test_build_record_command_mp3_includes_bitrate_and_duration_cap() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=3600,
    )
    assert "libmp3lame" in args
    assert "192k" in args
    assert "3600" in args
    assert "-t" in args


def test_build_record_command_flac_has_no_bitrate_flag() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.flac"),
        format="flac",
        bitrate_kbps=192,
        duration_seconds=60,
    )
    assert "flac" in args
    assert "192k" not in args


def test_save_and_load_settings_round_trip(tmp_path: Path) -> None:
    settings = RecordingSettings(format="ogg", bitrate_kbps=128)
    save_recording_settings(tmp_path, settings)
    reloaded = load_recording_settings(tmp_path)
    assert reloaded == settings


def test_load_settings_missing_file_returns_defaults(tmp_path: Path) -> None:
    assert load_recording_settings(tmp_path) == RecordingSettings()


# -- RadioRecorder (fake ffmpeg process, no real network/subprocess) -------


class _FakeProcess:
    """Stands in for subprocess.Popen: stays 'alive' until stop() is asked
    for gracefully (writes to stdin) or terminate() is called."""

    def __init__(self) -> None:
        self._alive = threading.Event()
        self._alive.set()
        self.stdin = _FakeStdin(self)
        self.terminated = False

    def poll(self) -> int | None:
        return None if self._alive.is_set() else 0

    def wait(self, timeout: float | None = None) -> int:
        deadline = time.monotonic() + (timeout or 30.0)
        while self._alive.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
        if self._alive.is_set():
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout or 0)
        return 0

    def terminate(self) -> None:
        self.terminated = True
        self._alive.clear()


class _FakeStdin:
    def __init__(self, process: _FakeProcess) -> None:
        self._process = process

    def write(self, data: bytes) -> None:
        if data == b"q":
            self._process._alive.clear()

    def flush(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _fake_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: "ffmpeg")


def test_start_raises_when_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: None)
    recorder = RadioRecorder()
    with pytest.raises(RecordingError):
        recorder.start(
            station_name="WXYZ",
            stream_url="https://example.com/stream",
            settings=RecordingSettings(destination_root=str(tmp_path)),
        )


def test_start_launches_and_reports_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    states: list[tuple[bool, Path | None]] = []
    recorder = RadioRecorder(on_state_changed=lambda rec, dest: states.append((rec, dest)))
    dest = recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(destination_root=str(tmp_path)),
    )
    assert recorder.is_recording is True
    assert recorder.current_destination == dest
    assert states == [(True, dest)]
    recorder.stop()
    time.sleep(0.05)
    assert recorder.is_recording is False


def test_start_refuses_when_already_recording(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    recorder = RadioRecorder()
    recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(destination_root=str(tmp_path)),
    )
    with pytest.raises(RecordingError):
        recorder.start(
            station_name="Other",
            stream_url="https://example.com/other",
            settings=RecordingSettings(destination_root=str(tmp_path)),
        )
    recorder.stop()


def test_stop_is_a_noop_when_not_recording() -> None:
    recorder = RadioRecorder()
    recorder.stop()  # no raise
    assert recorder.is_recording is False

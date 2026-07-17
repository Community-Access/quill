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
        temp_dir="E:/scratch/radio",
        filename_pattern="{station}_{date}",
        max_duration_minutes=45,
    )
    restored = RecordingSettings.from_dict(original.to_dict())
    assert restored == original
    assert restored.temp_dir == "E:/scratch/radio"


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


def test_build_record_command_includes_user_agent_before_input() -> None:
    # quill-radio #6: the recorder identifies as Quill Radio, and the UA is an
    # input option, so it must sit before -i.
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        user_agent="Quill Radio/1.1.0 (+https://example)",
    )
    assert "-user_agent" in args
    ua_index = args.index("-user_agent")
    assert args[ua_index + 1] == "Quill Radio/1.1.0 (+https://example)"
    assert ua_index < args.index("-i")


def test_build_record_command_default_loglevel_is_error() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
    )
    assert args[args.index("-loglevel") + 1] == "error"


def test_build_record_command_debug_uses_verbose_loglevel() -> None:
    # quill-radio #5: debug mode records at -loglevel verbose so the connection
    # and codec decisions land in the log.
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        loglevel="verbose",
    )
    assert args[args.index("-loglevel") + 1] == "verbose"


def test_build_record_command_unknown_loglevel_falls_back_to_error() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        loglevel="chatty",
    )
    assert args[args.index("-loglevel") + 1] == "error"


def test_drain_stderr_logs_lines_redacted_and_by_severity(caplog: pytest.LogCaptureFixture) -> None:
    # quill-radio #4/#5: ffmpeg's live stderr is drained to the log so it can
    # never stall the pipe, error-shaped lines at WARNING, the rest at DEBUG,
    # and a stream token in a URL is redacted.
    class _FakeStderr:
        def __init__(self, lines: list[bytes]) -> None:
            self._lines = iter(lines)

        def readline(self) -> bytes:
            return next(self._lines, b"")

        def close(self) -> None:
            pass

    class _FakeProcess:
        def __init__(self, lines: list[bytes]) -> None:
            self.stderr = _FakeStderr(lines)

    lines = [
        b"Opening 'https://cdn.example.com/s?token=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2'\n",
        b"Failed to reconnect to server\n",
        b"",
    ]
    recorder = RadioRecorder()
    with caplog.at_level("DEBUG", logger="quill.core.radio.recording"):
        recorder._drain_stderr(_FakeProcess(lines), "WQXR")  # type: ignore[arg-type]
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    debugs = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert any("Failed to reconnect" in r.getMessage() for r in warnings)
    assert any("Opening" in r.getMessage() for r in debugs)
    assert not any("a1b2c3d4e5f6" in r.getMessage() for r in caplog.records)
    assert any("[TOKEN]" in r.getMessage() for r in debugs)


def test_finalize_move_relocates_finished_recording(tmp_path: Path) -> None:
    # quill-radio #5: a finished recording moves from the temp dir to its home.
    temp = tmp_path / "temp"
    home = tmp_path / "home"
    temp.mkdir()
    src = temp / "show.mp3"
    src.write_bytes(b"audio")
    dst = home / "show.mp3"
    landed = recording._finalize_move(src, dst)
    assert landed == dst
    assert dst.read_bytes() == b"audio"
    assert not src.exists()


def test_finalize_move_missing_source_returns_destination(tmp_path: Path) -> None:
    src = tmp_path / "gone.mp3"
    dst = tmp_path / "home" / "gone.mp3"
    assert recording._finalize_move(src, dst) == dst


def test_build_record_command_no_user_agent_for_non_http_input() -> None:
    args = build_record_command(
        "ffmpeg",
        "file:///tmp/local.mp3",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        user_agent="Quill Radio/1.1.0 (+https://example)",
    )
    assert "-user_agent" not in args


def test_build_probe_codec_command_includes_user_agent_for_http() -> None:
    from quill.core.radio.recording import build_probe_codec_command

    args = build_probe_codec_command(
        "ffprobe", "https://example.com/stream", user_agent="Quill Radio/1.1.0 (+u)"
    )
    assert "-user_agent" in args
    assert args[args.index("-user_agent") + 1] == "Quill Radio/1.1.0 (+u)"
    # The URL stays the last argument.
    assert args[-1] == "https://example.com/stream"


def test_default_dir_is_a_visible_folder_under_music(tmp_path) -> None:
    # quill-radio #4: recordings default to ~/Music/Quill Radio Recordings, not
    # a buried AppData folder.
    from quill.core.radio.recording import _default_dir

    (tmp_path / "Music").mkdir()
    result = _default_dir(home=tmp_path)
    assert result == tmp_path / "Music" / "Quill Radio Recordings"


def test_default_dir_falls_back_to_home_without_music(tmp_path) -> None:
    from quill.core.radio.recording import _default_dir

    result = _default_dir(home=tmp_path)  # no Music folder
    assert result == tmp_path / "Quill Radio Recordings"


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


def test_build_record_command_omits_af_flag_by_default() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
    )
    assert "-af" not in args


def test_build_record_command_includes_af_flag_when_filter_graph_given() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        filter_graph="acompressor=threshold=-18dB",
    )
    af_index = args.index("-af")
    assert args[af_index + 1] == "acompressor=threshold=-18dB"
    assert args.index("-i") < af_index  # -af belongs to the output side, after -i


def test_build_record_command_copy_streams_verbatim() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mka"),
        format="copy",
        bitrate_kbps=192,
        duration_seconds=3600,
    )
    # -c:a copy, no re-encode, no bitrate, and still duration-capped.
    assert args[args.index("-c:a") + 1] == "copy"
    assert "192k" not in args
    assert "libmp3lame" not in args
    assert "-t" in args


def test_build_record_command_copy_ignores_filter_graph() -> None:
    # Nothing is decoded in a raw copy, so a Sound Enhancements filter can't
    # apply and must be dropped rather than produce a broken command.
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mka"),
        format="copy",
        bitrate_kbps=192,
        duration_seconds=60,
        filter_graph="acompressor=threshold=-18dB",
    )
    assert "-af" not in args
    assert args[args.index("-c:a") + 1] == "copy"


def test_build_probe_codec_command_targets_first_audio_stream() -> None:
    args = recording.build_probe_codec_command("ffprobe", "https://example.com/stream")
    assert args[0] == "ffprobe"
    assert "a:0" in args
    assert "stream=codec_name" in args
    assert args[-1] == "https://example.com/stream"


def test_parse_probe_codec_reads_first_nonblank_line_lowercased() -> None:
    assert recording.parse_probe_codec("\nMP3\n") == "mp3"
    assert recording.parse_probe_codec("") == ""


def test_raw_capture_extension_maps_known_codecs_and_falls_back() -> None:
    assert recording.raw_capture_extension("mp3") == "mp3"
    assert recording.raw_capture_extension("aac") == "aac"
    assert recording.raw_capture_extension("vorbis") == "ogg"
    assert recording.raw_capture_extension("opus") == "opus"
    assert recording.raw_capture_extension("flac") == "flac"
    # Unknown codec -> Matroska audio, the universal lossless copy container.
    assert recording.raw_capture_extension("some_new_codec") == "mka"


def test_record_format_labels_cover_every_format() -> None:
    from quill.core.radio.recording import RECORD_FORMAT_LABELS, RECORD_FORMATS

    assert set(RECORD_FORMAT_LABELS) == set(RECORD_FORMATS)


def test_start_copy_probes_extension_and_names_file_by_codec(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    # Stand in for the ffprobe subprocess: the stream is AAC.
    monkeypatch.setattr(recording, "_probe_capture_extension", lambda _url: "aac")
    recorder = RadioRecorder()
    dest = recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(format="copy", destination_root=str(tmp_path)),
    )
    assert dest.suffix == ".aac"
    recorder.stop()


def test_apply_sound_enhancements_defaults_off_and_round_trips() -> None:
    assert RecordingSettings().apply_sound_enhancements is False
    settings = RecordingSettings(apply_sound_enhancements=True)
    assert RecordingSettings.from_dict(settings.to_dict()).apply_sound_enhancements is True


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
        self.stderr = None  # a real Popen has this; the drain thread reads it
        self.returncode = 0  # a real Popen exposes this; _monitor reads it post-wait
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


def test_start_threads_filter_graph_into_the_ffmpeg_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: list[list[str]] = []

    def _fake_popen(args: list[str], **_kw: object) -> _FakeProcess:
        captured.append(args)
        return _FakeProcess()

    monkeypatch.setattr(recording.subprocess, "Popen", _fake_popen)
    recorder = RadioRecorder()
    recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(destination_root=str(tmp_path)),
        filter_graph="acompressor=threshold=-18dB",
    )
    recorder.stop()
    assert "-af" in captured[0]
    assert "acompressor=threshold=-18dB" in captured[0]


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


def test_reconnect_flags_only_for_http_and_when_enabled() -> None:
    from quill.core.radio.recording import build_record_command

    with_flags = build_record_command(
        "ffmpeg",
        "https://stream.example.com/live",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        reconnect_delay_max=10,
    )
    assert "-reconnect" in with_flags
    assert with_flags[with_flags.index("-reconnect_delay_max") + 1] == "10"

    disabled = build_record_command(
        "ffmpeg",
        "https://stream.example.com/live",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        reconnect_delay_max=0,
    )
    assert "-reconnect" not in disabled

    local_file = build_record_command(
        "ffmpeg",
        "C:/audio/local.mp3",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
        reconnect_delay_max=10,
    )
    assert "-reconnect" not in local_file


def test_reconnect_settings_round_trip_and_clamps() -> None:
    from quill.core.radio.recording import RecordingSettings

    settings = RecordingSettings(
        reconnect_enabled=False, reconnect_max_attempts=7, reconnect_wait_seconds=30
    )
    loaded = RecordingSettings.from_dict(settings.to_dict())
    assert loaded.reconnect_enabled is False
    assert loaded.reconnect_max_attempts == 7
    assert loaded.reconnect_wait_seconds == 30
    # Old settings files without the keys read as sensible defaults.
    legacy = RecordingSettings.from_dict({"format": "mp3"})
    assert legacy.reconnect_enabled is True
    assert legacy.reconnect_max_attempts == 5
    assert legacy.reconnect_wait_seconds == 10
    # Nonsense clamps rather than exploding.
    weird = RecordingSettings.from_dict({"reconnect_max_attempts": -3, "reconnect_wait_seconds": 0})
    assert weird.reconnect_max_attempts == 0
    assert weird.reconnect_wait_seconds == 1

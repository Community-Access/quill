"""Tests for quill_radio_mac.core.ffmpeg (discovery) and
quill_radio_mac.core.recording (filename building, command building, and
the recorder's start/stop/reconnect lifecycle).

No real ffmpeg process and no network: subprocess.Popen is monkeypatched
with a fake process, and ffmpeg/ffprobe discovery is monkeypatched via
env vars and search-dir lists. Golden argv assertions for
build_record_command are derived by reading upstream's own builder
(S:\\quill\\quill\\core\\radio\\recording.py::build_record_command).
"""

from __future__ import annotations

import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

import quill_radio_mac.core.recording as recording
from quill_radio_mac.core import ffmpeg
from quill_radio_mac.core.recording import (
    RadioRecorder,
    RecordingError,
    RecordingSettings,
    build_filename,
    build_record_command,
    load_recording_settings,
    save_recording_settings,
)

# -- ffmpeg discovery -------------------------------------------------------


def _clear_ffmpeg_env(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_FFMPEG", raising=False)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)


def test_install_hint_mentions_homebrew():
    assert "brew install ffmpeg" in ffmpeg.INSTALL_HINT


def test_ffmpeg_search_dirs_env_override_first(monkeypatch, tmp_path):
    _clear_ffmpeg_env(monkeypatch)
    monkeypatch.setenv("QUILL_FFMPEG", str(tmp_path / "override"))
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    dirs = ffmpeg.ffmpeg_search_dirs()
    assert dirs[0] == tmp_path / "override"


def test_ffmpeg_search_dirs_includes_bundle_and_engine_pack(monkeypatch, tmp_path):
    _clear_ffmpeg_env(monkeypatch)
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "bundle"))
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    dirs = ffmpeg.ffmpeg_search_dirs()
    assert tmp_path / "bundle" / "tools" / "ffmpeg" in dirs
    assert tmp_path / "data" / "engine-packs" / "ffmpeg" in dirs


def test_resolve_tool_finds_binary_in_search_dir(monkeypatch, tmp_path):
    managed = tmp_path / "tools" / "ffmpeg"
    managed.mkdir(parents=True)
    exe_name = "ffmpeg.exe" if ffmpeg.os.name == "nt" else "ffmpeg"
    (managed / exe_name).write_text("")
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [managed])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: None)
    found = ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG)
    assert found == str(managed / exe_name)


def test_resolve_tool_falls_back_to_path(monkeypatch, tmp_path):
    fake = tmp_path / "ffmpeg"
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: str(fake))
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) == str(fake)


def test_resolve_tool_rejects_disallowed_basename_from_path(monkeypatch):
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: "/usr/bin/eviltool")
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) is None


def test_resolve_tool_falls_back_to_homebrew_dirs(monkeypatch, tmp_path):
    # Bare "ffmpeg" (no extension) is checked as a candidate on every
    # platform (see _candidate_names); ".exe" is only an *additional*
    # candidate on nt, so this exercises the same code path everywhere.
    homebrew = tmp_path / "opt-homebrew" / "bin"
    homebrew.mkdir(parents=True)
    (homebrew / "ffmpeg").write_text("")
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: None)
    monkeypatch.setattr(ffmpeg, "_HOMEBREW_DIRS", (homebrew, tmp_path / "usr-local" / "bin"))
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) == str(homebrew / "ffmpeg")


def test_resolve_tool_search_dirs_win_before_homebrew(monkeypatch, tmp_path):
    managed = tmp_path / "managed"
    managed.mkdir()
    exe_name = "ffmpeg.exe" if ffmpeg.os.name == "nt" else "ffmpeg"
    (managed / exe_name).write_text("")
    homebrew = tmp_path / "homebrew"
    homebrew.mkdir()
    (homebrew / exe_name).write_text("")
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [managed])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: str(homebrew / exe_name))
    monkeypatch.setattr(ffmpeg, "_HOMEBREW_DIRS", (homebrew,))
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) == str(managed / exe_name)


def test_resolve_tool_none_when_nowhere_found(monkeypatch):
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: None)
    monkeypatch.setattr(ffmpeg, "_HOMEBREW_DIRS", ())
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) is None


def test_candidate_names_bare_only_on_posix(monkeypatch):
    monkeypatch.setattr(ffmpeg.os, "name", "posix")
    assert ffmpeg._candidate_names("ffmpeg") == ("ffmpeg",)


def test_candidate_names_bare_and_exe_on_nt(monkeypatch):
    monkeypatch.setattr(ffmpeg.os, "name", "nt")
    assert ffmpeg._candidate_names("ffmpeg") == ("ffmpeg", "ffmpeg.exe")


def test_find_ffmpeg_and_find_ffprobe_wrap_resolve_tool(monkeypatch, tmp_path):
    # find_ffmpeg/find_ffprobe are lru_cache-d; monkeypatch replaces the
    # cached function object itself (same pattern upstream's own ffmpeg
    # tests use), so no cache_clear() dance is needed.
    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: str(tmp_path / "ffmpeg"))
    monkeypatch.setattr(ffmpeg, "find_ffprobe", lambda: None)
    assert ffmpeg.find_ffmpeg() == str(tmp_path / "ffmpeg")
    assert ffmpeg.find_ffprobe() is None


def test_ffmpeg_available_reflects_find_ffmpeg(monkeypatch):
    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: "ffmpeg")
    assert ffmpeg.ffmpeg_available() is True
    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: None)
    assert ffmpeg.ffmpeg_available() is False


# -- RecordingSettings --------------------------------------------------


def test_settings_to_dict_from_dict_round_trip():
    original = RecordingSettings(
        format="ogg",
        bitrate_kbps=256,
        destination_root="D:/recordings",
        filename_pattern="{station}_{date}",
        max_duration_minutes=45,
    )
    restored = RecordingSettings.from_dict(original.to_dict())
    assert restored == original


def test_settings_from_dict_defaults_and_rejects_unknown_format():
    settings = RecordingSettings.from_dict({"format": "wma"})
    assert settings.format == "mp3"
    settings = RecordingSettings.from_dict({})
    assert settings.max_duration_minutes == 180


def test_apply_sound_enhancements_defaults_off_and_round_trips():
    assert RecordingSettings().apply_sound_enhancements is False
    settings = RecordingSettings(apply_sound_enhancements=True)
    assert RecordingSettings.from_dict(settings.to_dict()).apply_sound_enhancements is True


def test_reconnect_settings_round_trip_and_clamps():
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


def test_save_and_load_settings_round_trip(tmp_path):
    settings = RecordingSettings(format="ogg", bitrate_kbps=128)
    save_recording_settings(tmp_path, settings)
    reloaded = load_recording_settings(tmp_path)
    assert reloaded == settings


def test_load_settings_missing_file_returns_defaults(tmp_path):
    assert load_recording_settings(tmp_path) == RecordingSettings()


# -- build_filename -------------------------------------------------------


def test_build_filename_fills_tokens_and_sanitizes():
    when = datetime(2026, 7, 14, 8, 30, 0)
    name = build_filename("{station}: Live/Show? {date} {time}", station="WXYZ", when=when)
    assert name == "WXYZ LiveShow 2026-07-14 08-30-00"


def test_build_filename_falls_back_when_sanitized_to_empty():
    when = datetime(2026, 7, 14, 8, 30, 0)
    assert build_filename("???", station="", when=when) == "recording"


# -- build_record_command (golden argv, derived from upstream) ------------


def test_build_record_command_mp3_includes_bitrate_and_duration_cap():
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=3600,
    )
    assert args == [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "https://example.com/stream",
        "-vn",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        "-t",
        "3600",
        "-y",
        "out.mp3",
    ]


def test_build_record_command_flac_has_no_bitrate_flag():
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.flac"),
        format="flac",
        bitrate_kbps=192,
        duration_seconds=60,
    )
    assert args == [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "https://example.com/stream",
        "-vn",
        "-c:a",
        "flac",
        "-t",
        "60",
        "-y",
        "out.flac",
    ]


def test_build_record_command_omits_af_flag_by_default():
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=60,
    )
    assert "-af" not in args


def test_build_record_command_includes_af_flag_when_filter_graph_given():
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


def test_build_record_command_copy_streams_verbatim():
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mka"),
        format="copy",
        bitrate_kbps=192,
        duration_seconds=3600,
    )
    assert args == [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "https://example.com/stream",
        "-vn",
        "-c:a",
        "copy",
        "-t",
        "3600",
        "-y",
        "out.mka",
    ]


def test_build_record_command_copy_ignores_filter_graph():
    # Nothing is decoded in a raw copy, so a Sound Enhancements filter
    # can't apply and must be dropped rather than produce a broken command.
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


def test_build_record_command_bitrate_floor_is_32k():
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=8,
        duration_seconds=60,
    )
    assert args[args.index("-b:a") + 1] == "32k"


def test_build_record_command_duration_floor_is_one_second():
    args = build_record_command(
        "ffmpeg",
        "https://example.com/stream",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=192,
        duration_seconds=0,
    )
    assert args[args.index("-t") + 1] == "1"


def test_reconnect_flags_only_for_http_and_when_enabled():
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
    assert with_flags.index("-reconnect") < with_flags.index("-i")

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


def test_build_probe_codec_command_targets_first_audio_stream():
    args = recording.build_probe_codec_command("ffprobe", "https://example.com/stream")
    assert args == [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        "https://example.com/stream",
    ]


def test_parse_probe_codec_reads_first_nonblank_line_lowercased():
    assert recording.parse_probe_codec("\nMP3\n") == "mp3"
    assert recording.parse_probe_codec("") == ""


def test_raw_capture_extension_maps_known_codecs_and_falls_back():
    assert recording.raw_capture_extension("mp3") == "mp3"
    assert recording.raw_capture_extension("aac") == "aac"
    assert recording.raw_capture_extension("vorbis") == "ogg"
    assert recording.raw_capture_extension("opus") == "opus"
    assert recording.raw_capture_extension("flac") == "flac"
    # Unknown codec -> Matroska audio, the universal lossless copy container.
    assert recording.raw_capture_extension("some_new_codec") == "mka"


def test_record_format_labels_cover_every_format():
    from quill_radio_mac.core.recording import RECORD_FORMAT_LABELS, RECORD_FORMATS

    assert set(RECORD_FORMAT_LABELS) == set(RECORD_FORMATS)


# -- RadioRecorder (fake ffmpeg process, no real subprocess/network) ------


class _FakeProcess:
    """Stands in for subprocess.Popen: stays 'alive' until stop() is asked
    for gracefully (writes to stdin) or terminate() is called."""

    def __init__(self) -> None:
        self._alive = threading.Event()
        self._alive.set()
        self.stdin = _FakeStdin(self)
        self.terminated = False
        self.returncode = 0

    def poll(self):
        return None if self._alive.is_set() else self.returncode

    def wait(self, timeout=None):
        deadline = time.monotonic() + (timeout or 30.0)
        while self._alive.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
        if self._alive.is_set():
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout or 0)
        return self.returncode

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
def _fake_ffmpeg(monkeypatch):
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: "ffmpeg")


def test_start_raises_when_ffmpeg_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: None)
    recorder = RadioRecorder()
    with pytest.raises(RecordingError):
        recorder.start(
            station_name="WXYZ",
            stream_url="https://example.com/stream",
            settings=RecordingSettings(destination_root=str(tmp_path)),
        )


def test_start_launches_and_reports_state(monkeypatch, tmp_path):
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    states = []
    recorder = RadioRecorder(on_state_changed=lambda rec, dest: states.append((rec, dest)))
    dest = recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(destination_root=str(tmp_path)),
    )
    assert recorder.is_recording is True
    assert recorder.current_destination == dest
    assert recorder.current_station_name == "WXYZ"
    assert states == [(True, dest)]
    recorder.stop()
    time.sleep(0.05)
    assert recorder.is_recording is False


def test_start_threads_filter_graph_into_the_ffmpeg_command(monkeypatch, tmp_path):
    captured = []

    def _fake_popen(args, **_kw):
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


def test_start_refuses_when_already_recording(monkeypatch, tmp_path):
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


def test_stop_is_a_noop_when_not_recording():
    recorder = RadioRecorder()
    recorder.stop()  # no raise
    assert recorder.is_recording is False


def test_start_copy_probes_extension_and_names_file_by_codec(monkeypatch, tmp_path):
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    monkeypatch.setattr(recording, "_probe_capture_extension", lambda _url: "aac")
    recorder = RadioRecorder()
    dest = recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(format="copy", destination_root=str(tmp_path)),
    )
    assert dest.suffix == ".aac"
    recorder.stop()


def test_default_destination_root_uses_app_data_dir(monkeypatch, tmp_path):
    # No destination_root override: falls back to <data>/radio_recordings
    # rather than touching the real user's home directory.
    monkeypatch.delenv("QUILL_PORTABLE", raising=False)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    recorder = RadioRecorder()
    dest = recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(),
    )
    assert dest.parent == tmp_path / "data" / "radio_recordings"
    recorder.stop()


def test_continuation_filename_includes_part_number(monkeypatch, tmp_path):
    monkeypatch.setattr(recording.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    recorder = RadioRecorder()
    dest = recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(
            destination_root=str(tmp_path), filename_pattern="{station}"
        ),
        _continuation_part=1,
    )
    assert dest.name == "WXYZ (part 2).mp3"
    recorder.stop()


def test_monitor_triggers_reconnect_after_unclean_exit(monkeypatch, tmp_path):
    # A process that exits with a nonzero code (not via stop()) should
    # trigger a reconnect attempt callback; wait_seconds kept at the
    # settings minimum (1s) so the test stays fast.
    processes = [_FakeProcess(), _FakeProcess()]
    processes[0].returncode = 1  # first process "drops"

    def _fake_popen(args, **_kw):
        return processes.pop(0)

    monkeypatch.setattr(recording.subprocess, "Popen", _fake_popen)
    reconnects = []
    recorder = RadioRecorder(on_reconnect=lambda attempt, maximum: reconnects.append((attempt, maximum)))
    recorder.start(
        station_name="WXYZ",
        stream_url="https://example.com/stream",
        settings=RecordingSettings(
            destination_root=str(tmp_path), reconnect_wait_seconds=1, reconnect_max_attempts=2
        ),
    )
    # Simulate the connection dropping: flip the "alive" flag off directly
    # (not via stop(), so _user_stopped stays False and the monitor thread
    # treats this as an unclean exit).
    first_process = recorder._process
    first_process._alive.clear()
    deadline = time.monotonic() + 5.0
    while not reconnects and time.monotonic() < deadline:
        time.sleep(0.02)
    assert reconnects == [(1, 2)]
    recorder.stop()

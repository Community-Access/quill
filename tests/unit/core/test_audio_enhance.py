"""Tests for Sound Enhancements: filter-graph/command building (pure), the
relay's start/stop lifecycle (fake ffmpeg process, no real subprocess), and
the local HTTP relay's byte-streaming + single-consumer behavior (a real
loopback socket, but a fake byte source instead of real ffmpeg)."""

from __future__ import annotations

import functools
import subprocess
import threading
import time
import urllib.error
import urllib.request

import pytest

import quill.core.audio_enhance as audio_enhance
from quill.core.audio_enhance import (
    EnhanceError,
    EnhanceRelay,
    _RelayHTTPHandler,
    _RelayHTTPServer,
    build_filter_graph,
    build_relay_command,
    is_enhancement_active,
)

# -- pure filter-graph / command building ------------------------------------


def test_flat_preset_no_compressor_builds_empty_graph() -> None:
    assert build_filter_graph("Flat", compressor_enabled=False) == ""


def test_unknown_preset_falls_back_to_flat() -> None:
    assert build_filter_graph("Nonsense", compressor_enabled=False) == ""


def test_bass_boost_preset_includes_only_nonzero_bands() -> None:
    graph = build_filter_graph("Bass Boost", compressor_enabled=False)
    assert "f=100" in graph
    assert "g=7.0" in graph
    assert "f=1000" not in graph  # mid gain is 0 for Bass Boost


def test_compressor_alone_on_flat_preset() -> None:
    graph = build_filter_graph("Flat", compressor_enabled=True)
    assert graph.startswith("acompressor=")


def test_compressor_appended_after_eq_bands() -> None:
    graph = build_filter_graph("Voice Clarity", compressor_enabled=True)
    bands, _, compressor = graph.rpartition(",")
    assert "equalizer" in bands
    assert compressor.startswith("acompressor=")


def test_is_enhancement_active_false_for_flat_no_compressor() -> None:
    assert is_enhancement_active("Flat", compressor_enabled=False) is False


def test_is_enhancement_active_true_for_any_preset_or_compressor() -> None:
    assert is_enhancement_active("Bass Boost", compressor_enabled=False) is True
    assert is_enhancement_active("Flat", compressor_enabled=True) is True


def test_is_enhancement_active_true_for_smart_speed_alone() -> None:
    assert is_enhancement_active("Flat", compressor_enabled=False, smart_speed_enabled=True) is True


def test_smart_speed_alone_builds_only_the_silenceremove_filter() -> None:
    graph = build_filter_graph("Flat", compressor_enabled=False, smart_speed_enabled=True)
    assert graph.startswith("silenceremove=")
    assert "equalizer" not in graph
    assert "acompressor" not in graph


def test_smart_speed_appended_after_eq_and_compressor() -> None:
    graph = build_filter_graph("Podcast", compressor_enabled=True, smart_speed_enabled=True)
    parts = graph.split(",")
    assert "equalizer" in parts[0]
    assert parts[-2].startswith("acompressor=")
    assert parts[-1].startswith("silenceremove=")


def test_radio_never_engages_smart_speed_by_default() -> None:
    # Radio callers never pass smart_speed_enabled -- confirm the default is off.
    assert build_filter_graph("Bass Boost", compressor_enabled=True) == build_filter_graph(
        "Bass Boost", compressor_enabled=True, smart_speed_enabled=False
    )


def test_build_relay_command_adds_reconnect_flags_for_http() -> None:
    args = build_relay_command(
        "ffmpeg", "https://example.com/stream", eq_preset="Flat", compressor_enabled=False
    )
    assert "-reconnect" in args


def test_build_relay_command_skips_reconnect_flags_for_local_file() -> None:
    args = build_relay_command(
        "ffmpeg", "C:/music/episode.mp3", eq_preset="Flat", compressor_enabled=False
    )
    assert "-reconnect" not in args


def test_build_relay_command_omits_af_flag_when_nothing_engaged() -> None:
    args = build_relay_command(
        "ffmpeg", "https://example.com/stream", eq_preset="Flat", compressor_enabled=False
    )
    assert "-af" not in args


def test_build_relay_command_includes_af_flag_when_engaged() -> None:
    args = build_relay_command(
        "ffmpeg", "https://example.com/stream", eq_preset="Podcast", compressor_enabled=True
    )
    assert "-af" in args
    assert args[-3:] == ["-f", "mp3", "pipe:1"]


def test_build_relay_command_omits_ss_flag_by_default() -> None:
    args = build_relay_command("ffmpeg", "episode.mp3", eq_preset="Flat", compressor_enabled=False)
    assert "-ss" not in args


def test_build_relay_command_adds_ss_flag_before_input_when_seeking() -> None:
    args = build_relay_command(
        "ffmpeg",
        "episode.mp3",
        eq_preset="Flat",
        compressor_enabled=False,
        start_seconds=42.5,
    )
    ss_index = args.index("-ss")
    assert args[ss_index + 1] == "42.500"
    assert args.index("-i") > ss_index  # -ss must precede -i for fast input seeking


def test_build_relay_command_includes_af_flag_for_smart_speed_alone() -> None:
    args = build_relay_command(
        "ffmpeg",
        "episode.mp3",
        eq_preset="Flat",
        compressor_enabled=False,
        smart_speed_enabled=True,
    )
    af_index = args.index("-af")
    assert args[af_index + 1].startswith("silenceremove=")


def test_probe_source_duration_ms_returns_zero_when_ffprobe_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.core.speech.ffmpeg as speech_ffmpeg

    monkeypatch.setattr(speech_ffmpeg, "find_ffprobe", lambda: None)
    assert audio_enhance.probe_source_duration_ms("episode.mp3") == 0


def test_probe_source_duration_ms_parses_ffprobe_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.speech.ffmpeg as speech_ffmpeg
    import quill.stability.safe_subprocess as safe_subprocess

    monkeypatch.setattr(speech_ffmpeg, "find_ffprobe", lambda: "ffprobe")

    class _Completed:
        stdout = "123.456\n"

    monkeypatch.setattr(safe_subprocess, "run_subprocess_safely", lambda *a, **k: _Completed())
    assert audio_enhance.probe_source_duration_ms("episode.mp3") == 123456


# -- EnhanceRelay lifecycle (fake ffmpeg process) ----------------------------


class _FakeProcess:
    def __init__(self) -> None:
        self._alive = threading.Event()
        self._alive.set()
        self.stdout = _EmptySource()
        self.terminated = False

    def poll(self) -> int | None:
        return None if self._alive.is_set() else 0

    def wait(self, timeout: float | None = None) -> int:
        deadline = time.monotonic() + (timeout or 5.0)
        while self._alive.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
        if self._alive.is_set():
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout or 0)
        return 0

    def terminate(self) -> None:
        self.terminated = True
        self._alive.clear()

    def kill(self) -> None:
        self.terminate()


class _EmptySource:
    def read(self, _size: int) -> bytes:
        return b""


@pytest.fixture(autouse=True)
def _fake_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_enhance, "find_ffmpeg", lambda: "ffmpeg")


def test_start_raises_when_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_enhance, "find_ffmpeg", lambda: None)
    relay = EnhanceRelay()
    with pytest.raises(EnhanceError):
        relay.start("https://example.com/stream", eq_preset="Flat", compressor_enabled=True)


def test_start_returns_local_loopback_url_and_marks_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_enhance.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    relay = EnhanceRelay()
    try:
        url = relay.start(
            "https://example.com/stream", eq_preset="Bass Boost", compressor_enabled=False
        )
        assert url.startswith("http://127.0.0.1:")
        assert relay.is_active is True
    finally:
        relay.stop()
    assert relay.is_active is False


def test_start_accepts_smart_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def _fake_popen(args: list[str], **_kw: object) -> _FakeProcess:
        captured.append(args)
        return _FakeProcess()

    monkeypatch.setattr(audio_enhance.subprocess, "Popen", _fake_popen)
    relay = EnhanceRelay()
    try:
        relay.start(
            "episode.mp3", eq_preset="Flat", compressor_enabled=False, smart_speed_enabled=True
        )
    finally:
        relay.stop()
    assert "silenceremove=" in "".join(captured[0])


def test_stop_terminates_the_process(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _FakeProcess()
    monkeypatch.setattr(audio_enhance.subprocess, "Popen", lambda *a, **k: process)
    relay = EnhanceRelay()
    relay.start("https://example.com/stream", eq_preset="Flat", compressor_enabled=True)
    relay.stop()
    assert process.terminated is True


def test_stop_is_a_no_op_when_never_started() -> None:
    EnhanceRelay().stop()  # must not raise


def test_start_stops_any_previous_relay_first(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = [_FakeProcess(), _FakeProcess()]
    monkeypatch.setattr(audio_enhance.subprocess, "Popen", lambda *a, **k: processes.pop(0))
    relay = EnhanceRelay()
    try:
        relay.start("https://example.com/a", eq_preset="Flat", compressor_enabled=True)
        first_process = relay._process  # noqa: SLF001 - white-box lifecycle check
        relay.start("https://example.com/b", eq_preset="Flat", compressor_enabled=True)
        assert first_process is not None and first_process.terminated is True
    finally:
        relay.stop()


# -- relay HTTP handler: real loopback socket, fake byte source -------------


class _BytesSource:
    def __init__(self, payload: bytes) -> None:
        self._remaining = payload

    def read(self, size: int) -> bytes:
        chunk, self._remaining = self._remaining[:size], self._remaining[size:]
        return chunk


def _start_relay_server(source: object) -> tuple[_RelayHTTPServer, threading.Thread]:
    read_lock = threading.Lock()
    handler = functools.partial(_RelayHTTPHandler, source=source, read_lock=read_lock)
    server = _RelayHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_relay_handler_streams_source_bytes_to_client() -> None:
    server, thread = _start_relay_server(_BytesSource(b"hello enhanced audio"))
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/enhanced.mp3", timeout=5) as resp:
            assert resp.read() == b"hello enhanced audio"
            assert resp.headers["Content-Type"] == "audio/mpeg"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_relay_handler_rejects_a_second_concurrent_connection() -> None:
    release = threading.Event()

    class _BlockingSource:
        def __init__(self) -> None:
            self._served_first_chunk = False

        def read(self, _size: int) -> bytes:
            if not self._served_first_chunk:
                self._served_first_chunk = True
                return b"first-chunk"
            release.wait(timeout=5)
            return b""

    server, thread = _start_relay_server(_BlockingSource())
    try:
        port = server.server_address[1]
        first = urllib.request.urlopen(f"http://127.0.0.1:{port}/enhanced.mp3", timeout=5)
        first.read(len(b"first-chunk"))  # make sure the first connection has the lock
        try:
            with pytest.raises(urllib.error.HTTPError) as excinfo:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/enhanced.mp3", timeout=5)
            assert excinfo.value.code == 409
        finally:
            release.set()
            first.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

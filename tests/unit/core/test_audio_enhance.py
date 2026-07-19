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

FLAT = (0.0, 0.0, 0.0)
BASS_BOOST = (7.0, 0.0, 1.0)
VOICE_CLARITY = (-3.0, 4.0, 2.0)
PODCAST = (-4.0, 3.0, 0.0)


def test_flat_bands_no_compressor_builds_empty_graph() -> None:
    assert build_filter_graph(*FLAT, compressor_enabled=False) == ""


def test_bands_clamped_to_supported_range() -> None:
    graph = build_filter_graph(50.0, 0.0, 0.0, compressor_enabled=False)
    assert "g=12.0" in graph


def test_bass_boost_bands_include_only_nonzero_bands() -> None:
    graph = build_filter_graph(*BASS_BOOST, compressor_enabled=False)
    assert "f=100" in graph
    assert "g=7.0" in graph
    assert "f=1000" not in graph  # mid gain is 0 for Bass Boost


def test_compressor_alone_on_flat_bands() -> None:
    graph = build_filter_graph(*FLAT, compressor_enabled=True)
    assert graph.startswith("acompressor=")


def test_compressor_appended_after_eq_bands() -> None:
    graph = build_filter_graph(*VOICE_CLARITY, compressor_enabled=True)
    bands, _, compressor = graph.rpartition(",")
    assert "equalizer" in bands
    assert compressor.startswith("acompressor=")


def test_is_enhancement_active_false_for_flat_no_compressor() -> None:
    assert is_enhancement_active(*FLAT, compressor_enabled=False) is False


def test_is_enhancement_active_true_for_any_band_or_compressor() -> None:
    assert is_enhancement_active(*BASS_BOOST, compressor_enabled=False) is True
    assert is_enhancement_active(*FLAT, compressor_enabled=True) is True


def test_is_enhancement_active_true_for_smart_speed_alone() -> None:
    assert is_enhancement_active(*FLAT, compressor_enabled=False, smart_speed_enabled=True) is True


def test_smart_speed_alone_builds_only_the_silenceremove_filter() -> None:
    graph = build_filter_graph(*FLAT, compressor_enabled=False, smart_speed_enabled=True)
    assert graph.startswith("silenceremove=")
    assert "equalizer" not in graph
    assert "acompressor" not in graph


def test_smart_speed_appended_after_eq_and_compressor() -> None:
    graph = build_filter_graph(*PODCAST, compressor_enabled=True, smart_speed_enabled=True)
    parts = graph.split(",")
    assert "equalizer" in parts[0]
    assert parts[-2].startswith("acompressor=")
    assert parts[-1].startswith("silenceremove=")


def test_radio_never_engages_smart_speed_by_default() -> None:
    # Radio callers never pass smart_speed_enabled -- confirm the default is off.
    assert build_filter_graph(*BASS_BOOST, compressor_enabled=True) == build_filter_graph(
        *BASS_BOOST, compressor_enabled=True, smart_speed_enabled=False
    )


def test_build_relay_command_adds_reconnect_flags_for_http() -> None:
    args = build_relay_command(
        "ffmpeg", "https://example.com/stream", **_bands(FLAT), compressor_enabled=False
    )
    assert "-reconnect" in args


def test_build_relay_command_skips_reconnect_flags_for_local_file() -> None:
    args = build_relay_command(
        "ffmpeg", "C:/music/episode.mp3", **_bands(FLAT), compressor_enabled=False
    )
    assert "-reconnect" not in args


def test_build_relay_command_omits_af_flag_when_nothing_engaged() -> None:
    args = build_relay_command(
        "ffmpeg", "https://example.com/stream", **_bands(FLAT), compressor_enabled=False
    )
    assert "-af" not in args


def test_build_relay_command_includes_af_flag_when_engaged() -> None:
    args = build_relay_command(
        "ffmpeg", "https://example.com/stream", **_bands(PODCAST), compressor_enabled=True
    )
    assert "-af" in args
    assert args[-3:] == ["-f", "mp3", "pipe:1"]


def test_build_relay_command_omits_ss_flag_by_default() -> None:
    args = build_relay_command("ffmpeg", "episode.mp3", **_bands(FLAT), compressor_enabled=False)
    assert "-ss" not in args


def test_build_relay_command_adds_ss_flag_before_input_when_seeking() -> None:
    args = build_relay_command(
        "ffmpeg",
        "episode.mp3",
        **_bands(FLAT),
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
        **_bands(FLAT),
        compressor_enabled=False,
        smart_speed_enabled=True,
    )
    af_index = args.index("-af")
    assert args[af_index + 1].startswith("silenceremove=")


def _bands(values: tuple[float, float, float]) -> dict[str, float]:
    bass, mid, treble = values
    return {"bass_db": bass, "mid_db": mid, "treble_db": treble}


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
        relay.start("https://example.com/stream", **_bands(FLAT), compressor_enabled=True)


def test_start_returns_local_loopback_url_and_marks_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_enhance.subprocess, "Popen", lambda *a, **k: _FakeProcess())
    relay = EnhanceRelay()
    try:
        url = relay.start(
            "https://example.com/stream", **_bands(BASS_BOOST), compressor_enabled=False
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
            "episode.mp3", **_bands(FLAT), compressor_enabled=False, smart_speed_enabled=True
        )
    finally:
        relay.stop()
    assert "silenceremove=" in "".join(captured[0])


def test_stop_terminates_the_process(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _FakeProcess()
    monkeypatch.setattr(audio_enhance.subprocess, "Popen", lambda *a, **k: process)
    relay = EnhanceRelay()
    relay.start("https://example.com/stream", **_bands(FLAT), compressor_enabled=True)
    relay.stop()
    assert process.terminated is True


def test_stop_is_a_no_op_when_never_started() -> None:
    EnhanceRelay().stop()  # must not raise


def test_start_stops_any_previous_relay_first(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = [_FakeProcess(), _FakeProcess()]
    monkeypatch.setattr(audio_enhance.subprocess, "Popen", lambda *a, **k: processes.pop(0))
    relay = EnhanceRelay()
    try:
        relay.start("https://example.com/a", **_bands(FLAT), compressor_enabled=True)
        first_process = relay._process  # noqa: SLF001 - white-box lifecycle check
        relay.start("https://example.com/b", **_bands(FLAT), compressor_enabled=True)
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


# -- channel mode (stereo/mono/left/right) + night mode (sound options) --------


def test_is_enhancement_active_true_for_channel_mode_or_night_mode_alone() -> None:
    from quill.core.audio_enhance import is_enhancement_active

    for mode in ("mono", "left", "right"):
        assert is_enhancement_active(0, 0, 0, compressor_enabled=False, channel_mode=mode), mode
    # Stereo (the default) engages nothing on its own.
    assert not is_enhancement_active(0, 0, 0, compressor_enabled=False, channel_mode="stereo")
    assert is_enhancement_active(0, 0, 0, compressor_enabled=False, night_mode_enabled=True)


def test_filter_graph_orders_channel_first_and_night_mode_last() -> None:
    from quill.core.audio_enhance import build_filter_graph

    graph = build_filter_graph(
        6.0, 0.0, 2.0, compressor_enabled=True, channel_mode="mono", night_mode_enabled=True
    )
    # channel routing feeds everything downstream; night mode levels the result.
    assert graph.startswith("pan=mono")
    assert graph.endswith("p=0.9")
    assert graph.index("pan=") < graph.index("equalizer")
    assert graph.index("acompressor") < graph.index("dynaudnorm")


def test_optilab_off_or_bypassed_adds_nothing() -> None:
    from quill.core.audio_enhance import build_filter_graph, is_enhancement_active

    # A real mode but the bypass off -> nothing engaged (the checkbox is a true
    # bypass that still remembers the chosen mode).
    assert (
        build_filter_graph(
            *FLAT, compressor_enabled=False, optilab_enabled=False, optilab_mode="podcast"
        )
        == ""
    )
    assert not is_enhancement_active(
        *FLAT, compressor_enabled=False, optilab_enabled=False, optilab_mode="podcast"
    )
    # Enabled but mode "off" -> also nothing.
    assert (
        build_filter_graph(
            *FLAT, compressor_enabled=False, optilab_enabled=True, optilab_mode="off"
        )
        == ""
    )


def test_optilab_modes_build_expected_chains() -> None:
    from quill.core.audio_enhance import build_filter_graph, is_enhancement_active

    podcast = build_filter_graph(
        *FLAT, compressor_enabled=False, optilab_enabled=True, optilab_mode="podcast"
    )
    assert is_enhancement_active(
        *FLAT, compressor_enabled=False, optilab_enabled=True, optilab_mode="podcast"
    )
    # Podcast: subsonic HPF, speech leveling, compression, bass tame, then a
    # lookahead limiter guarding the output (last).
    assert "highpass=f=30" in podcast
    assert "speechnorm=" in podcast
    assert "acompressor=" in podcast
    assert podcast.split(",")[-1].startswith("alimiter=")

    stream = build_filter_graph(
        *FLAT, compressor_enabled=False, optilab_enabled=True, optilab_mode="stream"
    )
    assert "dynaudnorm=" in stream
    assert stream.split(",")[-1].startswith("alimiter=")

    limiter = build_filter_graph(
        *FLAT, compressor_enabled=False, optilab_enabled=True, optilab_mode="limiter"
    )
    # Smooth Limiter is the lightest chain: a compressor then the limiter.
    assert limiter.startswith("acompressor=")
    assert limiter.split(",")[-1].startswith("alimiter=")


def test_optilab_input_zero_default_omits_volume_but_nonzero_adds_it() -> None:
    from quill.core.audio_enhance import build_filter_graph

    zero = build_filter_graph(
        *FLAT,
        compressor_enabled=False,
        optilab_enabled=True,
        optilab_mode="limiter",
        optilab_input_db=0.0,
    )
    assert "volume=" not in zero  # 0 dB is the default and changes nothing
    trimmed = build_filter_graph(
        *FLAT,
        compressor_enabled=False,
        optilab_enabled=True,
        optilab_mode="limiter",
        optilab_input_db=6.0,
    )
    assert trimmed.startswith("volume=6.00dB")


def test_optilab_auto_adapt_changes_the_chain() -> None:
    from quill.core.audio_enhance import build_filter_graph

    neutral = build_filter_graph(
        *FLAT,
        compressor_enabled=False,
        optilab_enabled=True,
        optilab_mode="podcast",
        optilab_auto_adapt=0,
    )
    adapted = build_filter_graph(
        *FLAT,
        compressor_enabled=False,
        optilab_enabled=True,
        optilab_mode="podcast",
        optilab_auto_adapt=100,
    )
    assert neutral != adapted  # adapt leans the leveling/density more assertive


def test_optilab_chain_comes_after_night_mode() -> None:
    from quill.core.audio_enhance import build_filter_graph

    graph = build_filter_graph(
        *FLAT,
        compressor_enabled=False,
        night_mode_enabled=True,
        optilab_enabled=True,
        optilab_mode="stream",
    )
    # Night mode levels first; OptiLab's own limiter guards the final output.
    assert graph.index("dynaudnorm=f=250") < graph.index("alimiter=")


def test_filter_graph_left_and_right_send_whole_mix_to_one_ear() -> None:
    from quill.core.audio_enhance import build_filter_graph

    left = build_filter_graph(0, 0, 0, compressor_enabled=False, channel_mode="left")
    right = build_filter_graph(0, 0, 0, compressor_enabled=False, channel_mode="right")
    # The whole stereo field (both source channels blended) goes to the chosen
    # output channel; the other output is silenced, so the listener hears all of
    # the audio in just one ear.
    assert left == "pan=stereo|c0=0.5*c0+0.5*c1|c1=0*c0"
    assert right == "pan=stereo|c0=0*c0|c1=0.5*c0+0.5*c1"


def test_filter_graph_empty_when_nothing_engaged_including_stereo() -> None:
    from quill.core.audio_enhance import build_filter_graph

    assert (
        build_filter_graph(
            0.0, 0.0, 0.0, compressor_enabled=False, channel_mode="stereo", night_mode_enabled=False
        )
        == ""
    )


def test_relay_command_threads_channel_and_night_mode_into_the_graph() -> None:
    from quill.core.audio_enhance import build_relay_command

    args = build_relay_command(
        "ffmpeg",
        "https://example.com/stream",
        bass_db=0.0,
        mid_db=0.0,
        treble_db=0.0,
        compressor_enabled=False,
        channel_mode="right",
        night_mode_enabled=True,
    )
    graph = args[args.index("-af") + 1]
    assert "pan=stereo|c0=0*c0|c1=0.5*c0+0.5*c1" in graph
    assert "dynaudnorm" in graph


def test_new_presets_exist_and_stay_within_slider_range() -> None:
    from quill.core.audio_enhance import EQ_BAND_MAX_DB, EQ_BAND_MIN_DB, EQ_PRESETS

    for name in ("Small Speakers", "Late Night"):
        assert name in EQ_PRESETS
        for gain in EQ_PRESETS[name]:
            assert EQ_BAND_MIN_DB <= gain <= EQ_BAND_MAX_DB

"""The live stream's queues, priming and on-air proof (Studio PRD BCAST-026, BCAST-027, MX-186).

Every test here uses fake sinks and fake encoders: nothing is spawned and
nothing leaves the machine.
"""

from __future__ import annotations

import queue
import threading
import time

import numpy as np
import pytest

from quill.core.streaming import StreamSettings
from quill.platform.windows import live_stream_mix as mix
from quill.platform.windows.live_stream import LiveStream
from quill.platform.windows.live_stream_air import (
    BACK_ON_AIR,
    ON_AIR,
    EncoderProgress,
    StreamRefused,
)

pytestmark = pytest.mark.timeout(60)

SECOND = mix.RATE * mix.CHANNELS * 2  # bytes of s16 stereo in one second


def _until(condition, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


# -- fakes ------------------------------------------------------------------------------


class _Lines:
    """An encoder's stderr: lines the test says, then end of file on exit."""

    def __init__(self) -> None:
        self._q: queue.Queue[bytes] = queue.Queue()

    def readline(self) -> bytes:
        return self._q.get()

    def say(self, *lines: str) -> None:
        for line in lines:
            self._q.put(line.encode() + b"\n")

    def end(self) -> None:
        self._q.put(b"")


class _Sink:
    """A pipe's stdin; ``hold`` makes every write wait up to that long."""

    def __init__(self, hold: float = 0.0) -> None:
        self.data = bytearray()
        self.hold = hold
        self.release = threading.Event()
        self.entered = threading.Event()

    def write(self, block: bytes) -> None:
        self.entered.set()
        if self.hold:
            self.release.wait(self.hold)
        self.data += block

    def flush(self) -> None:
        return None

    def close(self) -> None:
        self.release.set()


class _Proc:
    def __init__(self, stdin: _Sink | None = None) -> None:
        self.stdin = stdin or _Sink()
        self.stdout = None
        self.stderr = _Lines()
        self.code: int | None = None

    def poll(self) -> int | None:
        return self.code

    def exit(self, code: int = 1, *last_words: str) -> None:
        self.stderr.say(*last_words)
        self.code = code
        self.stderr.end()

    def kill(self) -> None:
        if self.code is None:
            self.exit(-9)

    def wait(self, timeout: float | None = None) -> int | None:
        if self.code is None:
            self.exit(0)
        return self.code


def _progress(proc: _Proc, seconds: float, size: int = 0) -> None:
    proc.stderr.say(
        f"total_size={size}", f"out_time_us={int(seconds * 1_000_000)}", "progress=continue"
    )


class _Show:
    """A LiveStream whose encoders and saved copy are fakes the test controls."""

    def __init__(self, monkeypatch, *, archive: bool = False, encoder_hold: float = 0.0, **kw):
        monkeypatch.setattr(LiveStream, "_first_wait", 0.05)
        monkeypatch.setattr(LiveStream, "_tick", 0.02)
        self.events: list[tuple[str, bool]] = []
        self.encoders: list[_Proc] = []
        self.archive = _Proc()
        self.encoder_hold = encoder_hold
        self.stream = LiveStream(
            StreamSettings(host="127.0.0.1", port=8000, mount="/live", **kw),
            "pw",
            ffmpeg="ffmpeg",
            sources=[],
            on_event=lambda text, failure: self.events.append((text, failure)),
            archive_path="show.flac" if archive else "",
        )
        monkeypatch.setattr(self.stream, "_popen", self._popen)

    def _popen(self, command, *, stdout):
        if command[-1] == "show.flac":
            return self.archive
        proc = _Proc(_Sink(self.encoder_hold))
        self.encoders.append(proc)
        return proc

    def said(self, text: str) -> int:
        return sum(1 for sentence, _failure in self.events if text in sentence)


# -- BCAST-026: separate writers --------------------------------------------------------


def test_a_sink_blocked_for_five_seconds_does_not_stall_the_saved_copy(monkeypatch):
    show = _Show(monkeypatch, archive=True, encoder_hold=5.0)
    show.stream.start()
    try:
        encoder = show.encoders[0]
        assert encoder.stdin.entered.wait(2)  # the stream's writer is now stuck
        time.sleep(0.6)
        assert len(encoder.stdin.data) == 0
        # The mix and the saved copy kept going while the network write waited.
        assert len(show.archive.stdin.data) >= int(0.4 * SECOND)
        assert show.stream.mixer.blocks >= 20
    finally:
        show.encoders[0].stdin.release.set()
        show.stream.stop()


def test_overflow_drops_only_the_stream_and_is_counted_and_said_once():
    held = threading.Event()
    entered = threading.Event()
    overflows: list[int] = []
    lags: list[float] = []

    def sink(_block: bytes) -> None:
        entered.set()
        held.wait(5)

    writer = mix.BlockWriter(
        "test-writer",
        sink,
        capacity=5,
        on_overflow=lambda: overflows.append(1),
        lag_after=0.08,
        on_lag=lags.append,
    )
    try:
        writer.put(b"first")
        assert entered.wait(2)
        for index in range(10):
            writer.put(bytes([index]))
        assert writer.dropped == 5
        assert overflows == [1]
        assert len(lags) == 1 and lags[0] >= 0.08
    finally:
        held.set()
        writer.close(drain=False, timeout=2)


def test_the_saved_copy_writer_drains_everything_on_close():
    written: list[bytes] = []
    writer = mix.BlockWriter("archive", written.append, capacity=1000)
    for index in range(200):
        writer.put(bytes([index % 256]))
    assert writer.close(drain=True, timeout=5)
    assert len(written) == 200 and writer.dropped == 0


# -- MX-186: priming, gaps and trims ----------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _burst(ms: int, value: int = 1000) -> bytes:
    frames = mix.RATE * ms // 1000
    return np.full(frames * 2, value, dtype=np.int16).tobytes()


def _block(mixer: mix.StreamMixer) -> np.ndarray:
    return np.frombuffer(mixer.mix_block(), dtype=np.int16)


def test_a_source_primes_to_100_ms_and_then_10_ms_bursts_never_gap():
    mixer = mix.StreamMixer({"loop": 0.0}, [], clock=_Clock())
    for _ in range(9):  # 90 ms: not primed yet
        mixer.push("loop", _burst(10), 2)
    assert not _block(mixer).any()  # silence while filling, and no audio lost
    mixer.push("loop", _burst(10), 2)  # 100 ms now
    for _ in range(50):
        block = _block(mixer)
        assert (block == 1000).all(), "a zero-filled block after priming"
        mixer.push("loop", _burst(10), 2)
        mixer.push("loop", _burst(10), 2)
    assert mixer.gaps == 0 and mixer.trims == 0


def test_running_dry_reprimes_and_a_quick_return_counts_as_a_gap():
    clock = _Clock()
    mixer = mix.StreamMixer({"mic": 0.0}, [], clock=clock)
    mixer.push("mic", _burst(100), 2)
    for _ in range(5):
        _block(mixer)
    assert not mixer.sources["mic"].primed  # ran dry
    clock.now += 0.2
    mixer.push("mic", _burst(20), 2)
    assert mixer.gaps == 1
    assert not _block(mixer).any()  # filling again rather than playing 20 ms and stopping
    # A source that went quiet for seconds (loopback with nothing playing) is not a gap.
    mixer.push("mic", _burst(100), 2)
    for _ in range(6):
        _block(mixer)
    clock.now += 5
    mixer.push("mic", _burst(20), 2)
    assert mixer.gaps == 1


def test_a_source_running_ahead_is_trimmed_to_the_target_and_counted():
    mixer = mix.StreamMixer({"fast": 0.0}, [], clock=_Clock())
    mixer.push("fast", _burst(1000), 2)
    source = mixer.sources["fast"]
    assert source.size == mix.PRIME
    assert mixer.trims == 1
    # It never creeps toward seconds of delay: pushing more keeps it bounded.
    for _ in range(100):
        mixer.push("fast", _burst(20), 2)
    assert source.size <= mix.TRIM_ABOVE


def test_the_timer_is_steered_by_the_reference_sources_delivered_samples():
    nominal = mix.BLOCK / mix.RATE
    mixer = mix.StreamMixer({"mic": 0.0}, [], reference="mic", clock=_Clock())
    assert mixer.period() == nominal  # not primed: plain timer
    mixer.push("mic", _burst(250), 2)  # deeper than target: mic runs fast
    _block(mixer)
    assert mixer.period() < nominal
    assert mixer.period() >= nominal * (1 - mix.MAX_STEER)
    slow = mix.StreamMixer({"mic": 0.0}, [], reference="mic", clock=_Clock())
    slow.push("mic", _burst(100), 2)
    _block(slow)  # 80 ms left, below target: mic runs slow
    assert slow.period() > nominal


# -- BCAST-027: on air only once audio is moving ----------------------------------------


def test_on_air_is_said_only_after_two_seconds_were_accepted(monkeypatch):
    show = _Show(monkeypatch)
    show.stream.start()
    try:
        encoder = show.encoders[0]
        time.sleep(0.2)
        assert show.said(ON_AIR) == 0  # connected, nothing taken
        assert show.stream.status_line().startswith("Connecting")
        _progress(encoder, 1.0)
        time.sleep(0.2)
        assert show.said(ON_AIR) == 0
        _progress(encoder, 2.0)
        assert _until(lambda: show.said(ON_AIR) == 1)
        _progress(encoder, 3.0)
        time.sleep(0.1)
        assert show.said(ON_AIR) == 1  # one sentence, never repeated
        assert show.stream.status_line().startswith("On air")
    finally:
        show.stream.stop()


def test_back_on_air_waits_for_audio_on_the_new_connection(monkeypatch):
    show = _Show(monkeypatch)
    show.stream.start()
    try:
        _progress(show.encoders[0], 2.5)
        assert _until(lambda: show.said(ON_AIR) == 1)
        show.encoders[0].exit(1, "Connection reset by peer")
        assert _until(lambda: len(show.encoders) == 2)
        time.sleep(0.2)
        assert show.said(BACK_ON_AIR) == 0
        assert show.stream.status_line().startswith("Reconnecting")
        _progress(show.encoders[1], 2.0)
        assert _until(lambda: show.said(BACK_ON_AIR) == 1)
    finally:
        show.stream.stop()


def test_a_server_that_stops_taking_sound_is_off_air_until_it_takes_two_more_seconds(
    monkeypatch,
):
    import quill.platform.windows.live_stream as live_stream

    monkeypatch.setattr(live_stream, "STALLED_SECONDS", 0.2)
    show = _Show(monkeypatch)
    show.stream.start()
    try:
        encoder = show.encoders[0]
        _progress(encoder, 2.0)
        assert _until(lambda: show.said(ON_AIR) == 1)
        # Nothing more is taken: the buffers have filled.
        assert _until(lambda: show.said("stopped taking sound") == 1)
        assert not show.stream.on_air
        assert show.stream.status_line().startswith("Off air")
        _progress(encoder, 3.0)
        time.sleep(0.1)
        assert show.said(BACK_ON_AIR) == 0  # one second more is not proof
        _progress(encoder, 4.1)
        assert _until(lambda: show.said(BACK_ON_AIR) == 1)
        assert len(show.encoders) == 1  # the connection itself was never dropped
    finally:
        show.stream.stop()


def test_shoutcast_counts_only_the_bytes_actually_sent():
    progress = EncoderProgress()
    for line in ("total_size=1000", "out_time_us=4000000", "progress=continue"):
        progress.feed(line)
    assert progress.accepted_seconds(counted_bytes=False) == 4.0
    progress.sent_bytes = 400
    assert progress.accepted_seconds(counted_bytes=True) == pytest.approx(1.6)
    progress.sent_bytes = 600
    assert progress.accepted_seconds(counted_bytes=True) >= 2.0


def test_a_refusal_on_the_third_attempt_stops_the_retries_with_the_reason(monkeypatch):
    show = _Show(monkeypatch)
    show.stream.start()
    try:
        show.encoders[0].exit(1, "Connection refused")
        assert _until(lambda: len(show.encoders) == 2)
        show.encoders[1].exit(1, "Connection timed out")
        assert _until(lambda: len(show.encoders) == 3)
        show.encoders[2].exit(
            1, "Error opening output icecast://source@127.0.0.1:8000/live: 401 Unauthorized"
        )
        assert _until(lambda: show.said("refused the user name or password") == 1)
        time.sleep(0.3)
        assert len(show.encoders) == 3  # no fourth attempt
        assert show.said("The stream has stopped") == 1
        assert show.stream.status_line().startswith("Stream stopped")
    finally:
        show.stream.stop()


def test_a_shoutcast_password_refused_on_a_retry_stops_there(monkeypatch):
    class _Sock:
        def sendall(self, _data):
            return None

        def close(self):
            return None

    class _Empty:
        def read(self, _n):
            return b""  # the connection ends at once

    calls: list[int] = []

    def login():
        calls.append(1)
        if len(calls) > 1:
            raise StreamRefused("The SHOUTcast server refused the password.")
        return _Sock()

    show = _Show(monkeypatch, kind="shoutcast")
    monkeypatch.setattr(show.stream, "_shoutcast_login", login)
    original = show._popen

    def popen(command, *, stdout):
        proc = original(command, stdout=stdout)
        proc.stdout = _Empty()
        return proc

    monkeypatch.setattr(show.stream, "_popen", popen)
    show.stream.start()
    try:
        assert _until(lambda: show.said("refused the password") == 1)
        time.sleep(0.3)
        assert len(calls) == 2
        assert show.stream.ended
    finally:
        show.stream.stop()

"""The pre-roll guard (xradio2 section 6.1): no network, no real ffmpeg.

Many stations play an advert to every new connection. These tests pin the two
halves of the guard: ffmpeg never re-requests a live stream inside one file,
and whatever opens two separate connections is cut from the front of every
part -- including the part a mid-recording reconnect starts, so a second
advert is never spliced into the show.
"""

from __future__ import annotations

import io
import random
import struct
import subprocess
import threading
import time
from pathlib import Path

import pytest

from quill.core.radio import recording, recording_preroll
from quill.core.radio.recording import RadioRecorder, RecordingSettings
from quill.core.radio.recording_commands import build_record_command
from quill.core.radio.recording_preroll import (
    HOP_SECONDS,
    Opening,
    build_opening_decode_command,
    build_trim_command,
    describe_trims,
    envelope_from_pcm,
    guard_applies,
    input_dropped,
    plan_trims,
    shared_opening,
)
from quill.core.radio.recording_preroll_guard import OpeningGuard

# -- synthetic loudness outlines ------------------------------------------------


def _outline(seed: int, seconds: float, *, low: float = -40.0, high: float = -8.0) -> list[float]:
    """A programme-like loudness outline: it moves, and it is audible."""
    rng = random.Random(seed)
    return [rng.uniform(low, high) for _ in range(round(seconds / HOP_SECONDS))]


AD = _outline(1, 12.0)


def _opening(*pieces: list[float], complete: bool = False) -> Opening:
    joined: list[float] = []
    for piece in pieces:
        joined.extend(piece)
    return Opening(envelope=tuple(joined), complete=complete)


# -- the command lines ------------------------------------------------------------


def test_recording_never_re_requests_a_live_stream_inside_one_file() -> None:
    args = build_record_command(
        "ffmpeg",
        "https://example.test/live",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=128,
        duration_seconds=600,
        reconnect_delay_max=10,
    )
    # -reconnect_streamed is what made ffmpeg open a fresh connection -- and so
    # take a fresh pre-roll -- in the middle of the file with nothing to mark it.
    assert "-reconnect_streamed" not in args
    assert "-reconnect" in args


def test_decode_command_reads_the_opening_as_8khz_mono_pcm() -> None:
    args = build_opening_decode_command("ffmpeg", "https://example.test/live", user_agent="UA")
    assert args[args.index("-i") + 1] == "https://example.test/live"
    assert args[args.index("-t") + 1] == str(recording_preroll.ANALYSE_SECONDS)
    assert args[args.index("-user_agent") + 1] == "UA"
    assert "-rw_timeout" in args
    assert args[-5:] == ["-ar", "8000", "-f", "s16le", "pipe:1"]
    local = build_opening_decode_command("ffmpeg", r"C:\rec\show.mp3", user_agent="UA")
    assert "-user_agent" not in local
    assert "-rw_timeout" not in local


def test_trim_command_is_a_stream_copy_from_the_cut() -> None:
    args = build_trim_command("ffmpeg", Path("a.mp3"), Path("a.trimming.mp3"), 12.0)
    assert args[args.index("-ss") + 1] == "12.00"
    assert args.index("-ss") < args.index("-i")
    assert args[args.index("-c") + 1] == "copy"
    assert args[-1] == "a.trimming.mp3"


# -- which recordings get a reference connection ---------------------------------


@pytest.mark.parametrize(
    ("stream_url", "capture_url", "expected"),
    [
        ("https://example.test/live", "https://example.test/live", True),
        ("http://example.test/live.mp3", "http://example.test/live.mp3", True),
        ("https://example.test/live.m3u8", "https://example.test/live.m3u8", False),
        ("C:\\music\\file.mp3", "C:\\music\\file.mp3", False),
        ("https://www.youtube.com/watch?v=abc", "https://media.test/a.m4a", False),
    ],
)
def test_guard_applies_only_to_live_http_streams(
    stream_url: str, capture_url: str, expected: bool
) -> None:
    assert guard_applies(stream_url, capture_url) is expected


# -- telling a dropped stream from a finished recording -------------------------


def test_input_dropped_reads_ffmpegs_last_words() -> None:
    # ffmpeg exits 0 when its input dies; this is all that says it did.
    assert input_dropped(["[in#0/mp3 @ 0] Error during demuxing: Error number -10054 occurred"])
    assert input_dropped(["Connection reset by peer"])
    assert not input_dropped([])
    assert not input_dropped(["[mp3float @ 0] Header missing"])


# -- the loudness outline ----------------------------------------------------------


def test_envelope_from_pcm_measures_loudness_per_50ms() -> None:
    loud = struct.pack("<400h", *([16384, -16384] * 200))
    silent = bytes(800)
    envelope = envelope_from_pcm(loud + silent + b"\x01")  # a stray odd byte is ignored
    assert len(envelope) == 2
    assert envelope[0] == pytest.approx(-6.02, abs=0.05)
    assert envelope[1] == -90.0


# -- the comparison ---------------------------------------------------------------


def test_the_same_opening_on_two_connections_is_found_and_measured() -> None:
    first = _opening(AD, _outline(2, 40.0))
    second = _opening(AD, _outline(3, 40.0))
    trim_a, trim_b = shared_opening(first, second)
    assert trim_a == pytest.approx(12.0, abs=0.3)
    assert trim_b == pytest.approx(12.0, abs=0.3)


def test_a_small_offset_and_a_level_change_still_match() -> None:
    # A re-encoded recording starts a few frames late and a little quieter
    # than the reference decoded straight from the station.
    rng = random.Random(9)
    shifted = [v - 2.0 + rng.uniform(-0.5, 0.5) for v in AD]
    first = _opening(AD, _outline(2, 40.0))
    second = _opening([-30.0, -30.0, -30.0], shifted, _outline(3, 40.0))
    trim_a, trim_b = shared_opening(first, second)
    assert trim_a == pytest.approx(12.0, abs=0.5)
    assert trim_b == pytest.approx(12.15, abs=0.5)


def test_a_station_with_no_pre_roll_is_left_alone() -> None:
    assert shared_opening(_opening(_outline(4, 60.0)), _opening(_outline(5, 60.0))) == (0.0, 0.0)


def test_shared_silence_is_not_evidence() -> None:
    silence = [-90.0] * 240
    first = _opening(silence, _outline(6, 40.0))
    second = _opening(silence, _outline(7, 40.0))
    assert shared_opening(first, second) == (0.0, 0.0)


def test_a_brief_resemblance_is_not_acted_on() -> None:
    short = AD[:50]  # 2.5 seconds
    assert shared_opening(
        _opening(short, _outline(8, 40.0)), _opening(short, _outline(9, 40.0))
    ) == (
        0.0,
        0.0,
    )


def test_a_match_longer_than_any_advert_is_not_trusted() -> None:
    loop = _outline(10, 75.0)
    assert shared_opening(_opening(loop), _opening(loop)) == (0.0, 0.0)


def test_plan_trims_compares_every_part_with_the_reference_and_each_other() -> None:
    reference = _opening(AD, _outline(20, 60.0))
    part_one = _opening(AD, _outline(21, 60.0))
    part_two = _opening(AD, _outline(22, 60.0))
    trims = plan_trims(reference, [part_one, part_two, None])
    assert trims[0] == pytest.approx(12.0, abs=0.3)
    assert trims[1] == pytest.approx(12.0, abs=0.3)
    assert trims[2] == 0.0
    # With no reference, two parts still prove the insert to each other.
    assert plan_trims(None, [part_one, part_two])[1] == pytest.approx(12.0, abs=0.3)
    # A lone part with nothing to compare against is never trimmed.
    assert plan_trims(None, [part_one]) == [0.0]


def test_describe_trims_says_what_was_removed_or_nothing() -> None:
    assert describe_trims([], 0) == ""
    one = describe_trims([12.2], 0)
    assert "about 12 seconds" in one
    assert "the start of the recording" in one
    assert "usually an advert" in one
    assert "the start of 2 parts" in describe_trims([12.0, 11.6], 0)
    assert "Removed 1 recording part" in describe_trims([], 1)


# -- the guard ------------------------------------------------------------------------


class _Fakes:
    """A decoder that knows each source's outline, and a trimmer that records."""

    def __init__(self, outlines: dict[str, Opening]) -> None:
        self.outlines = outlines
        self.trimmed: list[tuple[str, float]] = []
        self.decoded: list[str] = []
        self.trim_ok = True

    def decode(self, source: str) -> Opening | None:
        self.decoded.append(source)
        for key, opening in self.outlines.items():
            if key in source:
                return opening
        return None

    def trim(self, path: Path, seconds: float) -> bool:
        self.trimmed.append((path.name, seconds))
        return self.trim_ok


def _guard(fakes: _Fakes) -> OpeningGuard:
    return OpeningGuard(decode=fakes.decode, trim=fakes.trim, delay_seconds=0.0, wait_seconds=5.0)


def test_guard_trims_the_first_connections_advert_using_the_reference(tmp_path: Path) -> None:
    fakes = _Fakes({
        "example.test": _opening(AD, _outline(30, 60.0)),
        "show.mp3": _opening(AD, _outline(31, 60.0)),
    })
    guard = _guard(fakes)
    guard.begin("job", "https://example.test/live", "https://example.test/live")
    part = tmp_path / "show.mp3"
    kept, note = guard.strip("job", [part])
    assert kept == [part]
    assert len(fakes.trimmed) == 1
    assert fakes.trimmed[0][0] == "show.mp3"
    assert fakes.trimmed[0][1] == pytest.approx(12.0, abs=0.3)
    assert "about 12 seconds" in note


def test_guard_leaves_a_recording_alone_when_nothing_is_shared(tmp_path: Path) -> None:
    fakes = _Fakes({
        "example.test": _opening(_outline(32, 75.0)),
        "show.mp3": _opening(_outline(33, 75.0)),
    })
    guard = _guard(fakes)
    guard.begin("job", "https://example.test/live", "https://example.test/live")
    part = tmp_path / "show.mp3"
    assert guard.strip("job", [part]) == ([part], "")
    assert fakes.trimmed == []


def test_guard_does_nothing_for_a_recording_it_never_saw_begin(tmp_path: Path) -> None:
    fakes = _Fakes({"show": _opening(AD, _outline(34, 60.0))})
    part = tmp_path / "show.mp3"
    assert _guard(fakes).strip("unknown", [part]) == ([part], "")
    assert fakes.decoded == []


def test_guard_never_opens_a_reference_for_an_hls_stream(tmp_path: Path) -> None:
    fakes = _Fakes({})
    guard = _guard(fakes)
    guard.begin("job", "https://example.test/live.m3u8", "https://example.test/live.m3u8")
    time.sleep(0.05)
    assert fakes.decoded == []
    # And a lone part with no reference is not even decoded.
    assert guard.strip("job", [tmp_path / "show.mp3"]) == ([tmp_path / "show.mp3"], "")
    assert fakes.decoded == []


def test_guard_removes_a_continuation_part_that_was_only_the_advert(tmp_path: Path) -> None:
    part_one = tmp_path / "show.mp3"
    part_two = tmp_path / "show (part 2).mp3"
    part_two.write_bytes(b"advert")
    fakes = _Fakes({
        "part 2": _opening(AD, complete=True),
        "show.mp3": _opening(AD, _outline(35, 60.0)),
    })
    guard = _guard(fakes)
    guard.begin("job", "https://example.test/live.m3u8", "https://example.test/live.m3u8")
    kept, note = guard.strip("job", [part_one, part_two])
    assert kept == [part_one]
    assert not part_two.exists()
    assert fakes.trimmed[0][0] == "show.mp3"
    assert "the start of the recording" in note


def test_a_failed_trim_is_not_announced_as_done(tmp_path: Path) -> None:
    fakes = _Fakes({
        "example.test": _opening(AD, _outline(36, 60.0)),
        "show.mp3": _opening(AD, _outline(37, 60.0)),
    })
    fakes.trim_ok = False
    guard = _guard(fakes)
    guard.begin("job", "https://example.test/live", "https://example.test/live")
    part = tmp_path / "show.mp3"
    assert guard.strip("job", [part]) == ([part], "")


def test_the_suite_never_lets_a_default_guard_decode_for_real(tmp_path: Path) -> None:
    # tests/conftest.py swaps the module's own runners for inert fakes, so a
    # recorder built with no arguments cannot reach the network from a test.
    guard = OpeningGuard(delay_seconds=0.0, wait_seconds=1.0)
    guard.begin("job", "https://example.test/live", "https://example.test/live")
    part = tmp_path / "show.mp3"
    assert guard.strip("job", [part]) == ([part], "")


# -- the recorder: a reconnect mid-recording ------------------------------------


class _Stdin:
    def __init__(self, process: _Process) -> None:
        self._process = process

    def write(self, data: bytes) -> None:
        if data == b"q":
            self._process.alive.clear()

    def flush(self) -> None:
        pass


class _Process:
    """A fake ffmpeg: writes some audio to its output, then either drops (exit 0
    with ffmpeg's demux-error line, as a real dropped stream does) or runs until
    it is asked to quit."""

    def __init__(self, out_path: Path, *, drops: bool) -> None:
        out_path.write_bytes(b"\xff" * 20_000)
        self.alive = threading.Event()
        self.returncode = 0
        self.stdin = _Stdin(self)
        lines = b"[in#0/mp3 @ 0] Error during demuxing: Error number -10054 occurred\n"
        self.stderr = io.BytesIO(lines if drops else b"")
        if not drops:
            self.alive.set()

    def poll(self) -> int | None:
        return None if self.alive.is_set() else 0

    def wait(self, timeout: float | None = None) -> int:
        deadline = time.monotonic() + (timeout if timeout is not None else 30.0)
        while self.alive.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
        if self.alive.is_set():
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout or 0)
        return 0

    def terminate(self) -> None:
        self.alive.clear()


def test_a_reconnect_mid_recording_does_not_splice_a_second_advert(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(recording, "find_ffmpeg", lambda: "ffmpeg")
    launched: list[_Process] = []

    def _popen(args: list[str], **_kw: object) -> _Process:
        process = _Process(Path(args[-1]), drops=not launched)
        launched.append(process)
        return process

    monkeypatch.setattr(recording.subprocess, "Popen", _popen)
    joined: list[list[Path]] = []

    def _join(parts: list[Path]) -> object:
        joined.append(list(parts))
        return _NoJoin()

    monkeypatch.setattr(recording, "join_recording_parts", _join)
    monkeypatch.setattr(recording, "describe_join", lambda _outcome: "")
    fakes = _Fakes({
        "example.test": _opening(AD, _outline(40, 60.0)),
        "(part 2)": _opening(AD, _outline(42, 60.0)),
        "WXYZ": _opening(AD, _outline(41, 60.0)),
    })
    notes: list[str] = []
    reconnects: list[tuple[int, int]] = []
    recorder = RadioRecorder(
        on_parts_joined=notes.append,
        on_reconnect=lambda attempt, maximum: reconnects.append((attempt, maximum)),
    )
    recorder._openings = _guard(fakes)
    recorder.start(
        station_name="WXYZ",
        stream_url="https://example.test/live",
        settings=RecordingSettings(
            destination_root=str(tmp_path), reconnect_wait_seconds=1, reconnect_max_attempts=2
        ),
        duration_minutes=60,
    )
    # The first ffmpeg exits 0 at once with a demux error: that is a drop, and
    # the recorder starts a continuation part on a new connection.
    deadline = time.monotonic() + 10
    while len(launched) < 2 and time.monotonic() < deadline:
        time.sleep(0.02)
    assert len(launched) == 2, "a dropped stream (ffmpeg exit 0) must reconnect"
    assert reconnects == [(1, 2)]
    recorder.stop()
    deadline = time.monotonic() + 10
    while not joined and time.monotonic() < deadline:
        time.sleep(0.02)
    assert len(joined) == 1
    names = [path.name for path in joined[0]]
    assert len(names) == 2
    assert "(part 2)" in names[1]
    # Both connections' adverts were cut before the parts were joined, so the
    # second one cannot land in the middle of the show.
    trimmed = dict(fakes.trimmed)
    assert set(trimmed) == set(names)
    for seconds in trimmed.values():
        assert seconds == pytest.approx(12.0, abs=0.3)
    assert any("the start of 2 parts" in note for note in notes)


class _NoJoin:
    joined = False
    path = None

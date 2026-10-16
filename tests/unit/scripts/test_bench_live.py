"""Recorded audio through dictation's real worker and controller (B-3, B-4, B-5).

The engine and the voice detector are fakes (a square tone of a known length
is a known phrase); everything between them -- the recogniser's worker
thread, its lead-in history, the controller, the shared ExternalDocument -- is
the real code. Nothing is typed anywhere: the field is a FakeTarget.
"""

from __future__ import annotations

import collections
import importlib
import sys
import time
from pathlib import Path
from typing import Any

import pytest

np = pytest.importorskip("numpy")

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
RATE = 16_000


def _live() -> Any:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("bench_live")


def _tone(seconds: float) -> Any:
    wave = np.sin(np.arange(int(seconds * RATE)) * 2 * np.pi * 220 / RATE)
    return np.where(wave >= 0, 0.3, -0.3).astype(np.float32)


#: A fake engine: the length of the loud part, in tenths of a second, says
#: what was "heard".
_HEARD = {
    10: "hello there",
    14: "new paragraph",
    18: "second line",
    22: "scratch that",
    26: "last words",
}


def _fake_transcribe(_engine: str, samples: Any, _language: str = "en") -> str:
    loud = int(np.sum(np.abs(np.asarray(samples)) > 0.1))
    return _HEARD.get(round(loud / 1600), "")


class _Segment:
    def __init__(self, start: int, samples: Any) -> None:
        self.start = start
        self.samples = samples


class _FakeVad:
    """Silero's surface, by loudness: speech is any block above 0.01 RMS, and a
    phrase ends after *pause* seconds of quiet."""

    def __init__(self, pause: float = 0.8) -> None:
        self._quiet_needed = max(1, int(pause * RATE / 512))
        self._segments: collections.deque[_Segment] = collections.deque()
        self._speaking = False
        self._quiet = 0
        self._held: list[Any] = []
        self._position = 0
        self._start = 0

    def accept_waveform(self, chunk: Any) -> None:
        loud = float(np.sqrt(np.mean(np.square(chunk)))) > 0.01
        if loud:
            if not self._speaking:
                self._speaking, self._start, self._held = True, self._position, []
            self._held.append(chunk)
            self._quiet = 0
        elif self._speaking:
            self._held.append(chunk)
            self._quiet += 1
            if self._quiet >= self._quiet_needed:
                self._close()
        self._position += len(chunk)

    def _close(self) -> None:
        speech = self._held[: len(self._held) - self._quiet] or self._held
        self._segments.append(_Segment(self._start, np.concatenate(speech)))
        self._speaking, self._quiet, self._held = False, 0, []

    def is_speech_detected(self) -> bool:
        return self._speaking

    def empty(self) -> bool:
        return not self._segments

    @property
    def front(self) -> _Segment:
        return self._segments[0]

    def pop(self) -> None:
        self._segments.popleft()

    def flush(self) -> None:
        if self._speaking:
            self._close()

    def reset(self) -> None:
        self._speaking, self._quiet, self._held = False, 0, []


@pytest.fixture()
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.windows_dictation import local_recognizer

    monkeypatch.setattr(local_recognizer, "_vad", lambda pause=0.8: _FakeVad(pause))
    monkeypatch.setattr(local_recognizer, "_load", lambda *_a, **_k: object())
    monkeypatch.setattr(local_recognizer, "transcribe", _fake_transcribe)


def _clips(*seconds: float) -> list[Any]:
    live = _live()
    return [live.Clip(f"{n}.wav", _tone(s), _HEARD[round(s * 10)]) for n, s in enumerate(seconds)]


# -- the stream ------------------------------------------------------------------ #


def test_the_recorded_stream_plays_every_clip_between_hiss_never_zeros() -> None:
    live = _live()
    blocks: list[Any] = []
    clips = _clips(1.0, 1.8)
    stream = live.RecordedStream(
        lambda data, *_a: blocks.append(data[:, 0].copy()), clips, pace=0, gap=0.2, tail=0.2
    )
    stream.start()
    assert stream.finished.wait(5)
    stream.close()
    assert stream.closed
    assert all(block.size == 512 and block.any() for block in blocks)
    assert clips[0].started <= clips[0].ended <= clips[1].started <= clips[1].ended


# -- latency, through the real worker ------------------------------------------------ #


def test_latency_is_measured_per_clip_through_the_real_worker(fake_engine: None) -> None:
    live = _live()
    clips = _clips(1.0, 1.8)
    listener = live.LatencyListener()
    recognizer = live.recorded_recognizer(
        listener,
        "moonshine",
        clips,
        post=lambda function, *args: function(*args),
        pace=4.0,
        gap=1.0,
        tail=1.5,
        pause_seconds=0.5,
    )
    recognizer.start("")
    assert recognizer.recorded.finished.wait(10)
    deadline = time.monotonic() + 5
    while len(listener.phrases) < 2 and time.monotonic() < deadline:
        time.sleep(0.05)
    recognizer.stop()
    report = live.latency_report(clips, listener)
    assert [row["heard"] for row in report["files"]] == ["hello there", "second line"]
    assert all(row["text_seconds"] is not None for row in report["files"])
    assert report["text_p95_seconds"] is not None and report["state_change_p95_seconds"] is not None
    assert report["microphone_lost"] == 0 and recognizer.reopened == 0
    assert recognizer.recorded.closed


def test_recorded_audio_never_starts_capturing_the_screen_reader(
    fake_engine: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The process's reader gate captures the running screen reader's audio;
    a benchmark must never open it."""
    from quill.core.windows_dictation import local_recognizer

    def refuse() -> None:
        raise AssertionError("the benchmark started the screen-reader capture")

    monkeypatch.setattr(local_recognizer, "reader_gate", refuse)
    live = _live()
    recognizer = live.recorded_recognizer(
        live.LatencyListener(), "moonshine", _clips(1.0), post=lambda f, *a: f(*a), pace=0
    )
    recognizer.start("")
    recognizer.stop()
    assert recognizer._gate.active is False


def test_latency_counts_from_the_speech_not_the_files_quiet_ends() -> None:
    live = _live()
    samples = np.concatenate([np.zeros(8_000), _tone(1.0), np.zeros(16_000)]).astype(np.float32)
    clip = live.Clip("a.wav", samples, "", started=100.0, pace=1.0)
    assert clip.speech_bounds() == (8_000, 24_000)
    assert clip.speech_started == pytest.approx(100.5)
    assert clip.speech_ended == pytest.approx(101.5)


def test_p95_is_the_nearest_rank() -> None:
    percentile = _live().percentile
    assert percentile(list(range(1, 101)), 95) == 95
    assert percentile([0.4], 95) == 0.4
    assert percentile([], 95) is None


# -- a whole session: the soak's machinery (B-3) ----------------------------------- #


def test_a_recorded_session_writes_each_phrase_once_and_never_types_a_command(
    fake_engine: None,
) -> None:
    live = _live()
    clips = _clips(1.0, 1.4, 1.8, 2.2, 2.6)
    session = live.run_session(
        clips, pace=4.0, gap=1.0, tail=1.5, pause=0.5, memory_every=0.2, settle=0.5
    )
    assert session.ui_errors == []
    assert session.phrases_per_clip() == [1, 1, 1, 1, 1]  # nothing lost, nothing doubled
    typed = " ".join(session.target.typed).lower()
    assert "paragraph" not in typed and "scratch" not in typed
    # "scratch that" took "second line" back; the paragraph break stayed.
    detail = (session.target.typed, session.target.erased, session.said)
    assert session.target.text == "Hello there.\n\nLast words", detail
    assert session.target.erased and session.microphone_closed
    assert session.reopened == 0


def test_memory_is_flat_unless_the_last_third_grew() -> None:
    flat = _live().memory_is_flat
    assert flat([200.0] * 9)
    assert flat([200, 201, 199, 202, 200, 203, 201, 204, 202])
    assert not flat([200, 200, 200, 260, 280, 300, 320, 340, 360])


# -- correction efficiency (B-5) --------------------------------------------------- #


def test_correction_efficiency_counts_utterances_per_corrected_error() -> None:
    efficiency = _live().correction_efficiency
    corrections = [
        {"wrong": "their car", "right": "the car", "utterances": ["scratch", "resay"]},
        {"wrong": "too", "right": "two", "utterances": ["scratch", "resay", "resay"]},
        {"wrong": "fore", "right": "four", "utterances": ["scratch"]},
    ]
    result = efficiency(corrections, "The car has two doors and fore wheels.")
    assert result == {"errors": 3, "corrected": 2, "utterances_per_corrected_error": 2.5}


def test_the_fake_target_never_sends_a_key() -> None:
    target = _live().FakeTarget()
    assert target.type_text("Hello. ") and target.backspace(2)
    assert target.text == "Hello"

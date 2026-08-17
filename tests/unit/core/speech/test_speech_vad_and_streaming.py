"""The silence pre-pass (speech_vad) and the streaming contract (streaming).

The pre-pass exists so a Whisper-family decoder is never handed silence to
hallucinate over; the streaming contract exists so a future streaming engine
can never make a screen reader speak the same words twice. Both are pure and
pinned here without any model or microphone.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from quill.core.speech.speech_vad import speech_span, trim_for_transcription
from quill.core.speech.streaming import StreamAnnouncer, StreamSnapshot

_RATE = 16000


def _write_wav(path: Path, segments: list[tuple[float, float]]) -> None:
    """Write mono 16-bit WAV from (seconds, amplitude 0..1) segments."""
    frames = bytearray()
    for seconds, amplitude in segments:
        count = int(seconds * _RATE)
        peak = int(amplitude * 20000)
        for i in range(count):
            value = int(peak * math.sin(2 * math.pi * 440 * i / _RATE)) if peak else 0
            frames += struct.pack("<h", value)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_RATE)
        wf.writeframes(bytes(frames))


# -- speech_span (pure) -------------------------------------------------------


def test_speech_span_finds_the_loud_region() -> None:
    values = [0.0] * 10 + [900.0] * 5 + [0.0] * 10
    assert speech_span(values) == (10, 14)


def test_speech_span_none_when_all_quiet() -> None:
    assert speech_span([10.0, 40.0, 5.0]) is None


# -- trim_for_transcription ---------------------------------------------------


def test_long_silence_around_speech_is_trimmed(tmp_path: Path) -> None:
    source = tmp_path / "take.wav"
    _write_wav(source, [(3.0, 0.0), (1.0, 0.9), (3.0, 0.0)])
    result = trim_for_transcription(source, tmp_path / "vad")
    assert not result.silent
    assert result.path != source
    assert result.trimmed_seconds > 4.0  # ~6s of quiet minus padding
    with wave.open(str(result.path), "rb") as wf:
        kept = wf.getnframes() / _RATE
    assert 1.0 <= kept <= 2.0  # the second of speech plus padding


def test_all_silence_reports_silent_and_keeps_original(tmp_path: Path) -> None:
    source = tmp_path / "quiet.wav"
    _write_wav(source, [(2.0, 0.0)])
    result = trim_for_transcription(source, tmp_path / "vad")
    assert result.silent
    assert result.path == source


def test_tight_recording_is_left_untouched(tmp_path: Path) -> None:
    source = tmp_path / "tight.wav"
    _write_wav(source, [(0.1, 0.0), (1.0, 0.9), (0.1, 0.0)])
    result = trim_for_transcription(source, tmp_path / "vad")
    assert not result.silent
    assert result.path == source  # savings under the rewrite threshold
    assert result.trimmed_seconds == 0.0


def test_unreadable_audio_passes_through(tmp_path: Path) -> None:
    source = tmp_path / "not-audio.wav"
    source.write_bytes(b"definitely not RIFF")
    result = trim_for_transcription(source, tmp_path / "vad")
    assert result.path == source
    assert not result.silent


# -- the streaming contract ---------------------------------------------------


def test_committed_text_is_announced_exactly_once() -> None:
    announcer = StreamAnnouncer()
    assert announcer.feed(StreamSnapshot("hello", "wor")) == "hello"
    assert announcer.feed(StreamSnapshot("hello world", "aga")) == " world"
    assert announcer.feed(StreamSnapshot("hello world", "again and")) == ""
    assert announcer.announced == "hello world"


def test_tentative_text_is_never_announced() -> None:
    announcer = StreamAnnouncer()
    announcer.feed(StreamSnapshot("", "the tentative tail"))
    assert announcer.announced == ""


def test_contract_violation_rebases_without_reannouncing() -> None:
    announcer = StreamAnnouncer()
    announcer.feed(StreamSnapshot("hello world"))
    # A misbehaving provider rewrites its committed prefix: nothing is spoken
    # for the rewrite, and later growth announces from the new base.
    assert announcer.feed(StreamSnapshot("hello, world")) == ""
    assert announcer.feed(StreamSnapshot("hello, world today")) == " today"


def test_reset_starts_a_new_utterance() -> None:
    announcer = StreamAnnouncer()
    announcer.feed(StreamSnapshot("first take"))
    announcer.reset()
    assert announcer.feed(StreamSnapshot("second")) == "second"

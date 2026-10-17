"""Long phrases reach a model that went silent on them (B-1, 2026-10-17).

A fake recogniser behaves as the measured Moonshine base did: no text at all
for more than 8.5 seconds of audio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from quill.core.windows_dictation import model_loader
from quill.core.windows_dictation.long_phrases import MAX_SECONDS, SplitLongPhrases, cut_points
from quill.core.windows_dictation.model_catalog import downloadable

RATE = 16_000


class _Inner:
    """Says how many seconds it heard, or nothing past 8.5 s."""

    def __init__(self) -> None:
        self.heard: list[float] = []

    def create_stream(self) -> Any:
        return _InnerStream()

    def decode_stream(self, stream: Any) -> None:
        seconds = len(stream.samples) / RATE
        self.heard.append(round(seconds, 2))
        stream.result.text = "" if seconds > 8.5 else f"piece of {seconds:.1f}"


class _InnerStream:
    def __init__(self) -> None:
        self.samples = np.zeros(0, dtype=np.float32)
        self.result = type("R", (), {"text": ""})()

    def accept_waveform(self, _rate: int, samples: Any) -> None:
        self.samples = np.concatenate([self.samples, np.asarray(samples, dtype=np.float32)])


def _speech(seconds: float, quiet_at: tuple[float, ...] = ()) -> Any:
    audio = np.full(int(RATE * seconds), 0.3, dtype=np.float32)
    for at in quiet_at:
        audio[int(RATE * at) : int(RATE * (at + 0.3))] = 0.0
    return audio


def test_a_short_phrase_passes_straight_through() -> None:
    inner = _Inner()
    wrapped = SplitLongPhrases(inner)
    stream = wrapped.create_stream()
    stream.accept_waveform(RATE, _speech(5.0))
    wrapped.decode_stream(stream)
    assert inner.heard == [5.0]
    assert stream.result.text == "piece of 5.0"


def test_a_long_phrase_is_heard_in_pieces_instead_of_lost() -> None:
    inner = _Inner()
    wrapped = SplitLongPhrases(inner)
    stream = wrapped.create_stream()
    stream.accept_waveform(RATE, _speech(12.0, quiet_at=(6.0,)))
    wrapped.decode_stream(stream)
    assert len(inner.heard) == 2 and all(s <= MAX_SECONDS for s in inner.heard)
    assert stream.result.text.count("piece of") == 2  # nothing lost


def test_the_cut_falls_in_the_quietest_moment() -> None:
    cuts = cut_points(_speech(12.0, quiet_at=(5.0,)), RATE)
    assert len(cuts) == 1 and 5.0 <= cuts[0] / RATE <= 5.3


def test_no_cut_is_needed_under_the_limit() -> None:
    assert cut_points(_speech(7.0), RATE) == []
    assert len(cut_points(_speech(30.0), RATE)) >= 4


def test_moonshine_base_loads_wrapped(tmp_path: Path) -> None:
    class _Sherpa:
        class OfflineRecognizer:
            @staticmethod
            def from_moonshine_v2(**_kw: Any) -> Any:
                return _Inner()

    built = model_loader.build(downloadable("moonshine_base"), tmp_path, _Sherpa(), threads=1)
    assert isinstance(built, SplitLongPhrases)

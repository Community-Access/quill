"""An offline recogniser that cannot take a long phrase, handed one in pieces.

**Why.** Moonshine base (sherpa-onnx's ``moonshine_v2`` kind, 1.13.8) writes
nothing for any phrase longer than about 8.5 seconds: the exported decoder's
encoder attention fails to broadcast ("2 by 498") inside ONNX Runtime,
sherpa-onnx catches it and returns an empty result, and nothing is said. Found
2026-10-22 on real speech: 50 to 73 percent of words "wrong" on every English
benchmark set, every one of them a recording over 8.5 seconds coming back
empty, while the first eight seconds of the same recordings came back right.
Dictation lets a phrase run to 20 seconds, so a long sentence simply vanished.

**What this does.** :class:`ChunkedOffline` answers in the offline shape the
rest of dictation uses (``create_stream`` / ``accept_waveform`` /
``decode_stream`` / ``result.text``). A phrase no longer than the model's limit
goes straight through. A longer one is cut into nearly equal pieces under the
limit, each cut moved to the quietest moment near it so a word is rarely split,
each piece is recognised on its own, and the words are joined with a space.

wx-free; numpy is imported where the audio is.
"""

from __future__ import annotations

from typing import Any

__all__ = ["ChunkedOffline", "split_points"]

RATE = 16_000
#: How far back from a planned cut to look for the quietest moment.
_SEARCH_SECONDS = 1.5
#: The frame quietness is measured over (20 ms).
_FRAME = RATE // 50


class _Result:
    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


class _HeldPhrase:
    """One phrase's audio, held until it is decoded."""

    def __init__(self) -> None:
        self.parts: list[Any] = []
        self.result = _Result("")

    def accept_waveform(self, rate: int, samples: Any) -> None:
        if rate != RATE:
            raise ValueError(f"dictation audio is {RATE} Hz, not {rate}")
        import numpy as np

        self.parts.append(np.asarray(samples, dtype=np.float32))


def split_points(audio: Any, max_samples: int) -> list[int]:
    """Where to cut *audio* so no piece is longer than *max_samples*.

    The pieces are nearly equal, and each cut is moved back to the quietest
    20 ms within :data:`_SEARCH_SECONDS` of where it would fall, never so far
    that a piece runs over the limit. Empty when no cut is needed.
    """
    import numpy as np

    total = len(audio)
    if total <= max_samples:
        return []
    search = min(int(RATE * _SEARCH_SECONDS), max_samples // 4)
    # Planned pieces leave room for each cut to move back by up to *search*
    # and still keep every piece, the last one included, within the limit.
    count = -(-total // (max_samples - search))
    step = total / count
    cuts: list[int] = []
    previous = 0
    for index in range(1, count):
        planned = int(round(index * step))
        low = max(previous + _FRAME, planned - search)
        best, quietest = planned, float("inf")
        for start in range(low, planned - _FRAME + 1, _FRAME):
            energy = float(np.mean(np.square(audio[start : start + _FRAME])))
            if energy < quietest:
                best, quietest = start + _FRAME // 2, energy
        cuts.append(best)
        previous = best
    return cuts


class ChunkedOffline:
    """*recognizer*, given at most *max_seconds* of a phrase at a time."""

    def __init__(self, recognizer: Any, max_seconds: float) -> None:
        self._recognizer = recognizer
        self._max_samples = int(RATE * max_seconds)

    def create_stream(self) -> _HeldPhrase:
        return _HeldPhrase()

    def _hear(self, piece: Any) -> str:
        stream = self._recognizer.create_stream()
        stream.accept_waveform(RATE, piece)
        self._recognizer.decode_stream(stream)
        result = stream.result
        text = result if isinstance(result, str) else getattr(result, "text", "")
        return str(text).strip()

    def decode_stream(self, phrase: _HeldPhrase) -> None:
        if not phrase.parts:
            phrase.result = _Result("")
            return
        import numpy as np

        audio = np.concatenate(phrase.parts)
        bounds = [0, *split_points(audio, self._max_samples), len(audio)]
        words = [self._hear(audio[a:b]) for a, b in zip(bounds, bounds[1:], strict=False)]
        phrase.result = _Result(" ".join(word for word in words if word))

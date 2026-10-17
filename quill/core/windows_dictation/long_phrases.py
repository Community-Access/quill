"""Long phrases for models that go silent on them (measured 2026-10-17).

On the B-1 benchmark (dictation design record section 35) the downloadable
Moonshine base -- sherpa-onnx's ``moonshine_v2`` export -- returned **no text
at all** for every recording longer than about 8.5 seconds (30 of 100
LibriSpeech test-clean recordings; the longest it transcribed was 8.2 s, the
shortest it dropped 8.7 s). Dictation cuts a phrase at a pause or at 20
seconds, so a long sentence spoken without a pause vanished without a word:
exactly what D-5 ("never lose what was said") forbids.

:class:`SplitLongPhrases` wraps such a recogniser in the same offline shape
(``create_stream``, ``accept_waveform``, ``decode_stream``, ``result.text``),
and decodes a phrase longer than :data:`MAX_SECONDS` as pieces cut at the
quietest moment the model can still hear whole, joined with a space. Shorter
phrases pass straight through, so nothing changes for them. wx-free; numpy is
imported only when a long phrase arrives.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

__all__ = ["MAX_SECONDS", "SplitLongPhrases", "cut_points"]

#: Longest piece handed to the model: under the ~8.5 s where it went silent.
MAX_SECONDS = 7.5
#: Never cut a piece shorter than this, so no piece is a lone syllable.
_MIN_SECONDS = 3.0
#: Loudness is judged over windows this long when choosing a cut.
_WINDOW_SECONDS = 0.1


def cut_points(
    samples: Sequence[float] | Any, rate: int, *, longest: float = MAX_SECONDS
) -> list[int]:
    """Sample indexes to cut *samples* at: each piece at most *longest* seconds,
    cut at its quietest window between :data:`_MIN_SECONDS` and *longest*."""
    import numpy as np

    audio = np.asarray(samples, dtype=np.float32)
    window = max(1, int(rate * _WINDOW_SECONDS))
    limit = int(rate * longest)
    shortest = int(rate * _MIN_SECONDS)
    cuts: list[int] = []
    start = 0
    while len(audio) - start > limit:
        lo, hi = start + shortest, start + limit
        best, best_energy = hi, float("inf")
        for at in range(lo, hi - window + 1, window):
            energy = float(np.mean(audio[at : at + window] ** 2))
            if energy < best_energy:
                best, best_energy = at + window // 2, energy
        cuts.append(best)
        start = best
    return cuts


class _Stream:
    def __init__(self, owner: SplitLongPhrases) -> None:
        self._owner = owner
        self._parts: list[Any] = []
        self._rate = 16_000
        self._options: list[tuple[Any, ...]] = []
        self.result: Any = _Result("")

    def accept_waveform(self, rate: int, samples: Any) -> None:
        self._rate = int(rate)
        self._parts.append(samples)

    def set_option(self, *args: Any) -> None:
        self._options.append(args)

    def _decode(self) -> None:
        import numpy as np

        audio = (
            np.concatenate([np.asarray(p, dtype=np.float32) for p in self._parts])
            if self._parts
            else np.zeros(0, dtype=np.float32)
        )
        inner = self._owner.inner
        edges = [0, *cut_points(audio, self._rate, longest=self._owner.longest), len(audio)]
        texts: list[str] = []
        for begin, end in zip(edges, edges[1:], strict=False):
            stream = inner.create_stream()
            for option in self._options:
                if hasattr(stream, "set_option"):
                    stream.set_option(*option)
            stream.accept_waveform(self._rate, audio[begin:end])
            inner.decode_stream(stream)
            text = str(stream.result.text).strip()
            if text:
                texts.append(text)
        self.result = _Result(" ".join(texts))


class _Result:
    def __init__(self, text: str) -> None:
        self.text = text


class SplitLongPhrases:
    """*inner* (an offline sherpa-onnx recogniser), fed long phrases in pieces."""

    def __init__(self, inner: Any, *, longest: float = MAX_SECONDS) -> None:
        self.inner = inner
        self.longest = longest

    def create_stream(self) -> _Stream:
        return _Stream(self)

    def decode_stream(self, stream: _Stream) -> None:
        stream._decode()

    def decode_streams(self, streams: Sequence[_Stream]) -> None:
        for stream in streams:
            stream._decode()

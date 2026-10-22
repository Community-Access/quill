"""Moonshine base writes nothing past about 8.5 seconds; long phrases go in
pieces (chunked_offline). Found 2026-10-22 on real speech: every benchmark
recording over 8.5 seconds came back empty."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.windows_dictation.chunked_offline import RATE, ChunkedOffline, split_points


class _ShortOnly:
    """A recogniser like Moonshine base: empty past *limit* seconds, otherwise
    one word per second of audio it was given."""

    def __init__(self, limit: float = 8.5) -> None:
        self.limit = limit
        self.lengths: list[float] = []

    def create_stream(self) -> SimpleNamespace:
        stream = SimpleNamespace(samples=None, result=SimpleNamespace(text=""))
        stream.accept_waveform = lambda rate, s: setattr(stream, "samples", s)
        return stream

    def decode_stream(self, stream: SimpleNamespace) -> None:
        seconds = len(stream.samples) / RATE
        self.lengths.append(seconds)
        words = "" if seconds > self.limit else " ".join(["word"] * max(1, int(seconds)))
        stream.result = SimpleNamespace(text=words)


def _speech(seconds: float, quiet_at: tuple[float, ...] = ()) -> object:
    np = pytest.importorskip("numpy")  # the live-dictation extra, not in every CI leg
    audio = np.full(int(RATE * seconds), 0.3, dtype=np.float32)
    for at in quiet_at:
        start = int(RATE * at)
        audio[start : start + RATE // 10] = 0.0
    return audio


@pytest.mark.parametrize("seconds", [8.0, 8.01, 12.0, 16.0, 19.9, 20.0, 47.3])
def test_no_piece_is_ever_over_the_limit(seconds: float) -> None:
    limit = int(RATE * 8.0)
    audio = _speech(seconds)
    bounds = [0, *split_points(audio, limit), len(audio)]
    pieces = [b - a for a, b in zip(bounds, bounds[1:], strict=False)]
    assert max(pieces) <= limit, pieces
    assert sum(pieces) == len(audio)  # nothing dropped, nothing doubled


def test_a_cut_moves_to_the_quiet_moment() -> None:
    # 12 seconds, planned cut near 6 s, a pause at 5.2 s: the cut is in the pause.
    audio = _speech(12.0, quiet_at=(5.2,))
    (cut,) = split_points(audio, int(RATE * 8.0))
    assert int(RATE * 5.2) <= cut <= int(RATE * 5.3)


def test_a_short_phrase_goes_straight_through() -> None:
    inner = _ShortOnly()
    engine = ChunkedOffline(inner, 8.0)
    phrase = engine.create_stream()
    phrase.accept_waveform(RATE, _speech(5.0))
    engine.decode_stream(phrase)
    assert phrase.result.text == "word word word word word"
    assert inner.lengths == [5.0]


def test_a_long_phrase_is_no_longer_lost() -> None:
    inner = _ShortOnly()
    plain = inner.create_stream()
    plain.accept_waveform(RATE, _speech(12.0))
    inner.decode_stream(plain)
    assert plain.result.text == ""  # the bug, as Moonshine base had it

    engine = ChunkedOffline(_ShortOnly(), 8.0)
    phrase = engine.create_stream()
    phrase.accept_waveform(RATE, _speech(6.0))
    phrase.accept_waveform(RATE, _speech(6.0))  # audio may arrive in parts
    engine.decode_stream(phrase)
    assert phrase.result.text.count("word") >= 10
    assert "  " not in phrase.result.text


def test_an_empty_phrase_is_empty_and_the_rate_is_checked() -> None:
    engine = ChunkedOffline(_ShortOnly(), 8.0)
    phrase = engine.create_stream()
    engine.decode_stream(phrase)
    assert phrase.result.text == ""
    with pytest.raises(ValueError):
        phrase.accept_waveform(8_000, [0.0] * 8_000)


def test_the_loader_wraps_moonshine_base(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.windows_dictation import model_loader
    from quill.core.windows_dictation.model_catalog import downloadable

    made: list[dict[str, object]] = []

    class _Offline:
        @staticmethod
        def from_moonshine_v2(**kwargs: object) -> _ShortOnly:
            made.append(kwargs)
            return _ShortOnly()

    monkeypatch.setattr(
        model_loader,
        "_files",
        lambda model, folder: dict.fromkeys(("encoder", "decoder", "tokens"), "x"),
    )
    engine = model_loader.build(
        downloadable("moonshine_base"),
        Path("unused"),
        SimpleNamespace(OfflineRecognizer=_Offline),
    )
    assert isinstance(engine, ChunkedOffline)
    assert made and made[0]["provider"] == "cpu"

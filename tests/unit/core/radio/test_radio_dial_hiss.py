"""The dial's hiss clip: generated, deterministic, loopable, and as shipped."""

from __future__ import annotations

import io
import math
import struct
import wave

import pytest

from quill.core.radio import dial_hiss


def _samples(data: bytes) -> list[int]:
    with wave.open(io.BytesIO(data)) as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == dial_hiss.SAMPLE_RATE
        frames = audio.readframes(audio.getnframes())
    return list(struct.unpack(f"<{len(frames) // 2}h", frames))


@pytest.mark.parametrize("level", sorted(dial_hiss.LEVELS))
def test_shipped_clip_is_exactly_what_the_code_writes(level):
    shipped = dial_hiss.clip_path(level)
    assert shipped.is_file(), "run python -m quill.core.radio.dial_hiss"
    assert shipped.read_bytes() == dial_hiss.render_wav(level)


def test_render_is_deterministic():
    assert dial_hiss.render_wav("low") == dial_hiss.render_wav("low")


def test_medium_is_louder_than_low_and_both_are_quiet():
    def rms(level: str) -> float:
        values = _samples(dial_hiss.render_wav(level))
        return math.sqrt(sum(v * v for v in values) / len(values)) / 32767

    low, medium = rms("low"), rms("medium")
    assert 0.015 < low < medium < 0.1


def test_the_loop_seam_has_no_click():
    values = _samples(dial_hiss.render_wav("medium"))
    steps = [abs(b - a) for a, b in zip(values, values[1:], strict=False)]
    seam = abs(values[0] - values[-1])
    assert seam <= max(steps)


def test_unknown_level_means_low():
    assert dial_hiss.clip_path("loud") == dial_hiss.clip_path("low")

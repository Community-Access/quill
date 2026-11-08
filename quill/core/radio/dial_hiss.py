"""The soft hiss Quill Radio plays between stations while dial tuning connects.

The idea, "FM Sound Between Stations", comes from BlindRadio by serrebidev (MIT),
github.com/serrebidev/blindradio, doc/readme.md. No audio and no code is taken
from it: the clip is synthesized here, from a seeded random generator, so the
same code always writes the same bytes and the shipped files can be checked
against it (``tests/unit/core/radio/test_radio_dial_hiss.py``).

Two files, one per level, because the hiss plays at a fixed level whatever the
station's own volume, and the simplest fixed level is one baked into the file:
``quill/assets/audio/dial_hiss_low.wav`` and ``dial_hiss_medium.wav``.

The clip loops. Its last quarter second is cross-faded into its first, so the
seam has no click and no gap; a loop that clicks every two seconds is the
opposite of the soft, continuous sound a dial makes.

Regenerate with ``python -m quill.core.radio.dial_hiss``. wx-free, strict-typed,
no network.
"""

from __future__ import annotations

import io
import math
import random
import struct
import wave
from pathlib import Path

__all__ = ["LEVELS", "SAMPLE_RATE", "clip_path", "render_wav"]

SAMPLE_RATE = 22050
_LOOP_SECONDS = 2.0
_FADE_SECONDS = 0.25
_SEED = 20261107

#: Level id -> RMS amplitude as a fraction of full scale. Low sits about 32 dB
#: below full scale, Medium about 24: under speech, never over it.
LEVELS: dict[str, float] = {"low": 0.025, "medium": 0.063}


def clip_path(level: str) -> Path:
    """Where the shipped clip for *level* lives (an unknown level means low)."""
    chosen = level if level in LEVELS else "low"
    return Path(__file__).resolve().parents[2] / "assets" / "audio" / f"dial_hiss_{chosen}.wav"


def _noise(count: int) -> list[float]:
    """Softened white noise, normalised to unit RMS."""
    rng = random.Random(_SEED)
    low = 0.0
    out: list[float] = []
    for _ in range(count):
        white = rng.uniform(-1.0, 1.0)
        # One gentle low-pass: an untreated white-noise hiss is harsh, and the
        # dial sound people remember is softer than that.
        low = 0.62 * low + 0.38 * white
        out.append(low)
    rms = math.sqrt(sum(value * value for value in out) / max(1, len(out))) or 1.0
    return [value / rms for value in out]


def _looped(samples: list[float], fade: int) -> list[float]:
    """Cross-fade the tail into the head, so the clip loops without a seam."""
    body = samples[: len(samples) - fade]
    tail = samples[len(samples) - fade :]
    for index in range(fade):
        mix = index / fade
        body[index] = body[index] * mix + tail[index] * (1.0 - mix)
    return body


def render_wav(level: str) -> bytes:
    """The clip for *level*, as the bytes of a mono 16-bit PCM WAV file."""
    amplitude = LEVELS.get(level, LEVELS["low"])
    loop = int(SAMPLE_RATE * _LOOP_SECONDS)
    fade = int(SAMPLE_RATE * _FADE_SECONDS)
    samples = _looped(_noise(loop + fade), fade)
    frames = bytearray()
    for value in samples:
        frames.extend(struct.pack("<h", max(-32768, min(32767, round(value * amplitude * 32767)))))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(bytes(frames))
    return buffer.getvalue()


def _write_all() -> None:
    for level in LEVELS:
        clip_path(level).write_bytes(render_wav(level))


if __name__ == "__main__":
    _write_all()

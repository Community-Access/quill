"""Generate QUILL's original page-turn-like chapter transition sound."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22050
DURATION_SECONDS = 1.2
OUTPUT = Path(__file__).resolve().parents[1] / "quill" / "assets" / "audio" / "page_turn.wav"


def generate_page_turn(path: Path) -> None:
    """Write a reproducible, synthesized mono PCM cue without sampled audio."""
    rng = random.Random(20261027)
    count = int(SAMPLE_RATE * DURATION_SECONDS)
    previous = 0.0
    frames = bytearray()
    for i in range(count):
        time = i / SAMPLE_RATE
        noise = rng.uniform(-1.0, 1.0)
        previous = 0.55 * previous + 0.45 * noise
        rustle = noise - previous
        envelope = sum(
            strength * math.exp(-(((time - center) / width) ** 2))
            for center, width, strength in (
                (0.25, 0.13, 0.5),
                (0.55, 0.16, 1.0),
                (0.85, 0.12, 0.4),
            )
        )
        fade = min(1.0, i / (SAMPLE_RATE * 0.03), (count - 1 - i) / (SAMPLE_RATE * 0.08))
        sample = max(-32768, min(32767, int(rustle * envelope * fade * 12000)))
        frames.extend(struct.pack("<h", sample))
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(frames)


if __name__ == "__main__":
    generate_page_turn(OUTPUT)

"""
Generate QUILL Lite dictation earcons.

Uses only the Python standard library.
Outputs four mono, 16-bit PCM, 44.1 kHz WAV files:
- dictation-start.wav
- dictation-commit.wav
- dictation-stop.wav
- dictation-error.wav
"""

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100
MAX_AMP = 32767


def envelope(i: int, total: int, fade_ms: float = 8.0) -> float:
    """Short linear fade-in/fade-out to avoid clicks."""
    fade = max(1, int(SAMPLE_RATE * fade_ms / 1000))
    if i < fade:
        return i / fade
    if i >= total - fade:
        return max(0.0, (total - i - 1) / fade)
    return 1.0


def tone(freq: float, duration_ms: float, volume: float = 0.22) -> list[int]:
    total = max(1, int(SAMPLE_RATE * duration_ms / 1000))
    samples = []
    for i in range(total):
        t = i / SAMPLE_RATE
        value = math.sin(2 * math.pi * freq * t)
        value *= envelope(i, total)
        value *= volume
        samples.append(int(MAX_AMP * value))
    return samples


def silence(duration_ms: float) -> list[int]:
    return [0] * max(1, int(SAMPLE_RATE * duration_ms / 1000))


def mix(*tracks: list[int]) -> list[int]:
    length = max(len(track) for track in tracks)
    out = []
    for i in range(length):
        value = sum(track[i] if i < len(track) else 0 for track in tracks)
        value = max(-MAX_AMP, min(MAX_AMP, value))
        out.append(value)
    return out


def concat(*parts: list[int]) -> list[int]:
    result = []
    for part in parts:
        result.extend(part)
    return result


def write_wav(path: Path, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(struct.pack("<h", s) for s in samples))


def generate(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Start: two short ascending tones.
    start = concat(
        tone(520, 80, 0.20),
        silence(18),
        tone(760, 95, 0.20),
    )

    # Commit: very short, soft two-frequency chime.
    # It is intentionally quieter and shorter because it is heard frequently.
    commit = mix(
        tone(720, 55, 0.11),
        tone(960, 55, 0.07),
    )

    # Stop: descending mirror of the start sound.
    stop = concat(
        tone(760, 80, 0.20),
        silence(18),
        tone(520, 95, 0.20),
    )

    # Error: low double pulse, distinct but not loud.
    error = concat(
        tone(330, 85, 0.18),
        silence(45),
        tone(330, 110, 0.18),
    )

    write_wav(output_dir / "dictation-start.wav", start)
    write_wav(output_dir / "dictation-commit.wav", commit)
    write_wav(output_dir / "dictation-stop.wav", stop)
    write_wav(output_dir / "dictation-error.wav", error)


if __name__ == "__main__":
    generate(Path(__file__).resolve().parent)
    print("Generated QUILL Lite dictation earcons.")

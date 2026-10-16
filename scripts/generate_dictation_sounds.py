"""Generate the seven Windows Dictation earcons in the Ink sound pack.

Standard library only, and deterministic: the WAV files are output, never
hand-edited, so every tone can be read, changed and regenerated from the
constants below. ``--check`` fails when a committed file has drifted from what
this script would write (``tests/unit/scripts/test_dictation_sounds.py``).

The design is the one in ``docs/design/dictation for windows only`` (PRD
sections 23 to 27): short sine tones between 300 and 1000 Hz, fades so nothing
clicks, peaks well below full scale, and the phrase cue -- heard hundreds of
times an hour -- the shortest and quietest of the four session cues, with edges
slow enough that it is heard as a tone and never as a letter
(:data:`PHRASE_ATTACK_MS`). The working tick (2026-10-13), which repeats every
second while a phrase is being recognised, is shorter and quieter still.

Usage::

    python scripts/generate_dictation_sounds.py          # write
    python scripts/generate_dictation_sounds.py --check  # verify
"""

from __future__ import annotations

import argparse
import io
import math
import struct
import sys
import wave
from pathlib import Path

SAMPLE_RATE = 44100
MAX_AMP = 32767

PACK_DIR = Path(__file__).resolve().parents[1] / "quill" / "assets" / "sound_packs" / "ink"


def _envelope(i: int, total: int, fade_ms: float = 8.0) -> float:
    """A short linear fade in and out, so no tone starts or ends on a click."""
    fade = max(1, int(SAMPLE_RATE * fade_ms / 1000))
    if i < fade:
        return i / fade
    if i >= total - fade:
        return max(0.0, (total - i - 1) / fade)
    return 1.0


def tone(freq: float, duration_ms: float, volume: float) -> list[int]:
    total = max(1, int(SAMPLE_RATE * duration_ms / 1000))
    return [
        int(MAX_AMP * volume * _envelope(i, total) * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
        for i in range(total)
    ]


#: The phrase cue's slow edges. A tone that reaches full volume in a few
#: milliseconds is heard as a consonant: the first phrase cue (two tones mixed,
#: 55 ms, 8 ms fades) was reported as a spoken "c" before every read-back
#: (2026-10-12). Rising over 25 ms and dying over 60 ms, it is a tone and
#: nothing else.
PHRASE_ATTACK_MS = 25.0
PHRASE_RELEASE_MS = 60.0

#: The working tick: as slow to rise as the phrase cue, and over sooner.
WORKING_MS = 70.0
WORKING_ATTACK_MS = 25.0
WORKING_RELEASE_MS = 40.0


def soft_tone(
    freq: float, duration_ms: float, volume: float, attack_ms: float, release_ms: float
) -> list[int]:
    """A sine with a slow, curved rise and fall: no transient to hear as a letter."""
    total = max(1, int(SAMPLE_RATE * duration_ms / 1000))
    rise = max(1, int(SAMPLE_RATE * attack_ms / 1000))
    fall = max(1, int(SAMPLE_RATE * release_ms / 1000))

    def gain(i: int) -> float:
        if i < rise:
            return math.sin(0.5 * math.pi * i / rise) ** 2
        if i >= total - fall:
            return math.sin(0.5 * math.pi * max(0, total - i - 1) / fall) ** 2
        return 1.0

    return [
        int(MAX_AMP * volume * gain(i) * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
        for i in range(total)
    ]


def silence(duration_ms: float) -> list[int]:
    return [0] * max(1, int(SAMPLE_RATE * duration_ms / 1000))


def mix(*tracks: list[int]) -> list[int]:
    length = max(len(track) for track in tracks)
    return [
        max(-MAX_AMP, min(MAX_AMP, sum(track[i] if i < len(track) else 0 for track in tracks)))
        for i in range(length)
    ]


def concat(*parts: list[int]) -> list[int]:
    return [sample for part in parts for sample in part]


def sounds() -> dict[str, list[int]]:
    """File name -> samples, for all seven earcons."""
    return {
        # Two short ascending tones: listening.
        "windows_dictation_on.wav": concat(tone(520, 80, 0.20), silence(18), tone(760, 95, 0.20)),
        # One soft, round note: this phrase is in the document. Slow edges, so
        # it is never heard as a letter (PHRASE_ATTACK_MS).
        "windows_dictation_phrase.wav": soft_tone(
            880, 130, 0.12, PHRASE_ATTACK_MS, PHRASE_RELEASE_MS
        ),
        # The start sound, descending: no longer listening.
        "windows_dictation_off.wav": concat(tone(760, 80, 0.20), silence(18), tone(520, 95, 0.20)),
        # A low double pulse: needs attention. Distinct, not loud.
        "windows_dictation_error.wav": concat(
            tone(330, 85, 0.18), silence(45), tone(330, 110, 0.18)
        ),
        # The working tick (2026-10-13): once a second while a heard phrase is
        # still being recognised, so the quietest and shortest of all. Low and
        # round, with the phrase cue's slow edges, so it is a tone and never a
        # consonant; and short, because the screen reader's gate does not
        # listen to the microphone while QUILL itself is making a sound.
        "windows_dictation_working.wav": soft_tone(
            520, WORKING_MS, 0.06, WORKING_ATTACK_MS, WORKING_RELEASE_MS
        ),
        # The command word (2026-10-15, D-1): a quick, higher rising pair when
        # "QUILL" or the Command Key is heard, and the same pair falling when
        # command mode ends. Shorter, higher and a little softer than the on
        # and off pair, so a command is never mistaken for dictation stopping,
        # and longer than the phrase cue, which is heard far more often.
        "windows_dictation_command_on.wav": concat(
            tone(880, 55, 0.16), silence(12), tone(1175, 75, 0.16)
        ),
        "windows_dictation_command_off.wav": concat(
            tone(1175, 55, 0.16), silence(12), tone(880, 75, 0.16)
        ),
    }


def encode(samples: list[int]) -> bytes:
    """Mono, 16-bit PCM, 44.1 kHz WAV bytes."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return buffer.getvalue()


def drifted(directory: Path = PACK_DIR) -> list[str]:
    """Names of the earcons whose committed bytes differ from the generator's."""
    return [
        name
        for name, samples in sounds().items()
        if not (directory / name).is_file() or (directory / name).read_bytes() != encode(samples)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a file has drifted")
    args = parser.parse_args(argv)
    if args.check:
        stale = drifted()
        if stale:
            print(
                "Out of date: " + ", ".join(stale) + ". Run scripts/generate_dictation_sounds.py."
            )
            return 1
        print("Dictation earcons are up to date.")
        return 0
    for name, samples in sounds().items():
        (PACK_DIR / name).write_bytes(encode(samples))
    print(f"Wrote {len(sounds())} dictation earcons to {PACK_DIR}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

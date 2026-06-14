"""Generate QUILL indentation tone WAV files for all four built-in scales.

Each scale produces 8 levels × 2 directions (up/down) = 16 WAV files per
pack. Four packs are generated:

    quill/assets/sound_packs/indent_pentatonic/
    quill/assets/sound_packs/indent_whole_tone/
    quill/assets/sound_packs/indent_diatonic/
    quill/assets/sound_packs/indent_chromatic/

Each pack is a *partial* QSP: it defines only the indent_level events and
ships no earcons. Combine with the Ink earcon pack for full audio feedback.

Tone design (issue #182)
------------------------
- Bell synthesis: sine fundamental + inharmonic partial at 2.76× fundamental,
  -12 dB relative to fundamental.
- Attack noise transient: spectrally shaped for direction cue.
  - Going deeper (up): high-pass noise 4-8 kHz  — brief upward hiss
  - Dedenting  (down): low-pass noise 80-400 Hz  — brief downward thud
- ADSR: attack=3 ms, decay=20 ms, sustain=0.25, release=40 ms → 83 ms total.
- Volume: -18 dBFS (amplitude 0.126).

Run from the repo root:
    python scripts/gen_indent_tones.py
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SR = 44100
VOL = 10 ** (-18 / 20)  # -18 dBFS

PACK_ROOT = Path(__file__).parent.parent / "quill" / "assets" / "sound_packs"

# ---------------------------------------------------------------------------
# Scale definitions: 8 frequencies per scale (Hz), C5=523.25 root
# ---------------------------------------------------------------------------

SCALES: dict[str, tuple[float, ...]] = {
    "pentatonic": (
        523.25,  # C5
        587.33,  # D5
        659.26,  # E5
        784.00,  # G5
        880.00,  # A5
        1046.50,  # C6
        1174.66,  # D6
        1760.00,  # A6
    ),
    "whole_tone": (
        523.25,  # C5
        587.33,  # D5
        659.26,  # E5
        739.99,  # F#5
        830.61,  # G#5
        932.33,  # A#5
        1046.50,  # C6
        1174.66,  # D6
    ),
    "diatonic": (
        523.25,  # C5
        587.33,  # D5
        659.26,  # E5
        698.46,  # F5
        784.00,  # G5
        880.00,  # A5
        987.77,  # B5
        1046.50,  # C6
    ),
    "chromatic": (
        523.25,  # C5
        554.37,  # C#5
        587.33,  # D5
        622.25,  # D#5
        659.26,  # E5
        698.46,  # F5
        739.99,  # F#5
        784.00,  # G5
    ),
}

SCALE_PRETTY: dict[str, str] = {
    "pentatonic": "Ink Pentatonic Tones",
    "whole_tone": "Ink Whole-Tone Tones",
    "diatonic": "Ink Diatonic Tones",
    "chromatic": "Ink Chromatic Tones",
}

SCALE_DESC: dict[str, str] = {
    "pentatonic": (
        "Indentation depth tones on a C5 pentatonic scale. "
        "Any two adjacent notes are harmonious; no dissonance possible. "
        "Recommended default for most users. "
        "Partial QSP: defines only indent_level events. "
        "Combine with the Ink earcon pack for full audio feedback."
    ),
    "whole_tone": (
        "Indentation depth tones on a C5 whole-tone scale. "
        "Equal 200-cent interval between every level — going deeper always "
        "sounds brighter, dedenting always darker. "
        "Partial QSP: defines only indent_level events."
    ),
    "diatonic": (
        "Indentation depth tones on C major (C5-C6). "
        "Familiar to most ears; semitone steps make adjacent levels clearly "
        "distinguishable at the cost of occasional mild tension. "
        "Partial QSP: defines only indent_level events."
    ),
    "chromatic": (
        "Indentation depth tones — one semitone per level from C5. "
        "Maximum pitch resolution for users working at 5+ nesting levels. "
        "Partial QSP: defines only indent_level events."
    ),
}


# ---------------------------------------------------------------------------
# Core synthesis primitives
# ---------------------------------------------------------------------------


def _clamp(s: float) -> int:
    return max(-32768, min(32767, int(s * 32767)))


def _write_wav(path: Path, samples: list[float]) -> None:
    data = b"".join(struct.pack("<h", _clamp(s)) for s in samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


def _ms(t_ms: float) -> int:
    return int(SR * t_ms / 1000)


def _adsr(i: int, n: int, atk: int, dec: int, sus: float, rel: int) -> float:
    if i < atk:
        return i / max(atk, 1)
    if i < atk + dec:
        return 1.0 - ((i - atk) / max(dec, 1)) * (1.0 - sus)
    if i < n - rel:
        return sus
    return sus * (n - i) / max(rel, 1)


def _edge(i: int, n: int, ramp_ms: float = 2.0) -> float:
    r = _ms(ramp_ms)
    return min(1.0, i / max(r, 1)) * min(1.0, (n - i) / max(r, 1))


# ---------------------------------------------------------------------------
# Directional noise transients
# ---------------------------------------------------------------------------

random.seed(42)


def _white_noise() -> float:
    return random.uniform(-1.0, 1.0)


def _hp_noise(prev: list[float]) -> float:
    """Single-pole high-pass (~4 kHz cutoff at 44.1 kHz): passes sharp attack hiss."""
    raw = _white_noise()
    # RC high-pass: y[n] = a * (y[n-1] + x[n] - x[n-1])
    a = 0.83  # pole ~4.5 kHz
    out = a * (prev[0] + raw - prev[1])
    prev[0] = out
    prev[1] = raw
    return out


def _lp_noise(prev: list[float]) -> float:
    """Single-pole low-pass (~300 Hz cutoff): warm downward thud."""
    raw = _white_noise()
    # RC low-pass: y[n] = (1-a)*x[n] + a*y[n-1]
    a = 0.958  # pole ~300 Hz
    out = (1.0 - a) * raw + a * prev[0]
    prev[0] = out
    return out


# ---------------------------------------------------------------------------
# Tone synthesis
# ---------------------------------------------------------------------------


def _bell_tone(freq: float, direction: str, n: int) -> list[float]:
    """Bell tone with ADSR and directional attack noise transient."""
    atk = _ms(3)
    dec = _ms(20)
    sus = 0.25
    rel = _ms(40)

    # Direction-cue noise burst: 10 ms at attack, -14 dB relative to bell
    noise_dur = _ms(10)
    noise_vol = 10 ** (-14 / 20)

    hp_state = [0.0, 0.0]
    lp_state = [0.0]

    out: list[float] = []
    for i in range(n):
        # Bell: fundamental + inharmonic partial at 2.76× (-12 dB)
        bell = math.sin(2 * math.pi * freq * i / SR)
        bell += 0.25 * math.sin(2 * math.pi * freq * 2.76 * i / SR)

        env = _adsr(i, n, atk, dec, sus, rel)
        sample = bell * env

        # Noise transient during attack window
        if i < noise_dur:
            t = 1.0 - i / noise_dur  # fades out over the window
            if direction == "up":
                noise = _hp_noise(hp_state) * t * noise_vol
            else:
                noise = _lp_noise(lp_state) * t * noise_vol
            sample += noise

        out.append(sample * _edge(i, n) * VOL)

    return out


# ---------------------------------------------------------------------------
# Pack generation
# ---------------------------------------------------------------------------


MANIFEST_TEMPLATE = """\
{{
  "format": "qsp",
  "version": "1",
  "name": {name},
  "author": "Jeff Bishop",
  "description": {desc},
  "license": "CC0",
  "events": {{
{events_block}
  }}
}}
"""


def _generate_pack(scale_key: str, freqs: tuple[float, ...]) -> None:
    pack_dir = PACK_ROOT / f"indent_{scale_key}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    duration_n = _ms(83)  # 3+20+20+40 ms (sustain segment ~20 ms)

    for level, freq in enumerate(freqs):
        for direction in ("up", "down"):
            wav_name = f"indent_{scale_key}_{level}_{direction}.wav"
            wav_path = pack_dir / wav_name
            samples = _bell_tone(freq, direction, duration_n)
            _write_wav(wav_path, samples)
            print(f"  {wav_name}")

    import json

    manifest = {
        "format": "qsp",
        "version": "1",
        "name": SCALE_PRETTY[scale_key],
        "author": "Jeff Bishop",
        "description": SCALE_DESC[scale_key],
        "license": "CC0",
        "events": {
            f"indent_level_{level}_{direction}": f"indent_{scale_key}_{level}_{direction}.wav"
            for level in range(len(freqs))
            for direction in ("up", "down")
        },
    }
    manifest_path = pack_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  manifest.json -> {pack_dir.name}/")


if __name__ == "__main__":
    print(f"Output root: {PACK_ROOT}")
    for scale_key, freqs in SCALES.items():
        print(f"\n--- {SCALE_PRETTY[scale_key]} ({scale_key}) ---")
        _generate_pack(scale_key, freqs)

    total = sum(len(freqs) * 2 for freqs in SCALES.values())
    print(f"\nDone. {total} WAV files generated across {len(SCALES)} packs.")

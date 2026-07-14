"""Transition earcons ("sounders") and PCM silence for chaptered speech (§4.8.5).

wx-free, strict-typed, stdlib-only (``wave`` + ``math`` + ``struct``). Produces a
short, pleasant **placeholder chime** to mark article/chapter boundaries in the
"with-tones" output variant, plus matching PCM silence for the inter-article gap.

The bundled chime is intentionally a *placeholder* the user can replace: a real
sound file dropped into a sound pack, or any WAV chosen in the batch dialog, can
override it. The generator is parameterised by sample rate / channels / sample
width so the earcon and silence always match the format of the speech WAVs they
are spliced between (the assembler reads the first section's format and passes it
through — see :mod:`quill.core.speech.chapter_assemble`).

No playback happens here — everything writes PCM to disk, consistent with the
silent batch pipeline (§silent-batch).
"""

from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

# A sensible default speech-WAV format. SAPI 5, Piper, eSpeak, and Kokoro all
# emit 16-bit mono; 22.05 kHz is the most common TTS rate. The assembler
# overrides these from the first real section WAV so splices line up exactly.
DEFAULT_SAMPLE_RATE = 22050
DEFAULT_CHANNELS = 1
DEFAULT_SAMPWIDTH = 2  # bytes per sample (16-bit PCM)


@dataclass(slots=True, frozen=True)
class PcmFormat:
    """The PCM parameters that silence and earcons must match to splice cleanly."""

    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = DEFAULT_CHANNELS
    sampwidth: int = DEFAULT_SAMPWIDTH

    @classmethod
    def from_wav(cls, path: Path) -> PcmFormat:
        """Read the PCM format of an existing WAV (the canonical section format)."""
        with wave.open(str(path), "rb") as w:
            return cls(
                sample_rate=w.getframerate(),
                channels=w.getnchannels(),
                sampwidth=w.getsampwidth(),
            )


def _max_amplitude(sampwidth: int) -> int:
    """Largest positive sample value for a given byte width (16-bit -> 32767)."""
    return (1 << (8 * sampwidth - 1)) - 1


def _tone_samples(
    fmt: PcmFormat,
    *,
    freq_hz: float,
    duration_ms: int,
    volume: float,
    fade_ms: int = 8,
) -> list[int]:
    """A single sine tone as a list of integer samples (mono), with a short fade.

    The fade in/out avoids clicks at the tone edges — important for screen-reader
    users who would otherwise hear a hard pop at every chapter boundary.
    """
    n = max(0, int(fmt.sample_rate * duration_ms / 1000))
    if n == 0:
        return []
    amp = _max_amplitude(fmt.sampwidth) * max(0.0, min(1.0, volume))
    fade = min(int(fmt.sample_rate * fade_ms / 1000), n // 2)
    samples: list[int] = []
    for i in range(n):
        env = 1.0
        if fade > 0:
            if i < fade:
                env = i / fade
            elif i >= n - fade:
                env = (n - i) / fade
        value = amp * env * math.sin(2.0 * math.pi * freq_hz * (i / fmt.sample_rate))
        samples.append(int(value))
    return samples


def _write_wav(path: Path, fmt: PcmFormat, mono_samples: list[int]) -> None:
    """Write mono integer samples to a PCM WAV, duplicating across channels."""
    clip = _max_amplitude(fmt.sampwidth)
    frames = bytearray()
    for s in mono_samples:
        s = max(-clip - 1, min(clip, s))
        packed = struct.pack("<h", s) if fmt.sampwidth == 2 else struct.pack("<i", s)
        frames += packed * fmt.channels
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(fmt.channels)
        w.setsampwidth(fmt.sampwidth)
        w.setframerate(fmt.sample_rate)
        w.writeframes(bytes(frames))


def silence_frames(fmt: PcmFormat, duration_ms: int) -> bytes:
    """Raw PCM silence (all-zero frames) of ``duration_ms`` in ``fmt``."""
    n = max(0, int(fmt.sample_rate * duration_ms / 1000))
    return b"\x00" * (n * fmt.sampwidth * fmt.channels)


def write_silence_wav(path: Path, fmt: PcmFormat, duration_ms: int) -> Path:
    """Write a silent WAV of ``duration_ms`` (used for the inter-article gap)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(fmt.channels)
        w.setsampwidth(fmt.sampwidth)
        w.setframerate(fmt.sample_rate)
        w.writeframes(silence_frames(fmt, duration_ms))
    return path


def default_sounder_samples(fmt: PcmFormat, *, volume: float = 1.0) -> list[int]:
    """The placeholder chime as mono samples: a rising two-note 'ding-dong'.

    Two short sine tones (a perfect fourth apart, ~A5 then D6) with a tiny gap —
    a friendly, unobtrusive boundary cue. Swap the frequencies/durations to taste,
    or replace the whole thing with a user-chosen sound later.
    """
    first = _tone_samples(fmt, freq_hz=880.0, duration_ms=110, volume=volume)
    middle = [0] * int(fmt.sample_rate * 0.02)  # 20 ms gap between the two notes
    second = _tone_samples(fmt, freq_hz=1174.7, duration_ms=150, volume=volume)
    return first + middle + second


def write_default_sounder(
    path: Path,
    fmt: PcmFormat | None = None,
    *,
    volume: float = 1.0,
) -> Path:
    """Write the placeholder transition chime to ``path`` as a PCM WAV.

    ``fmt`` defaults to the standard speech-WAV format; pass the section format so
    the chime splices cleanly. ``volume`` is 0.0–1.0 (map a 0–100 setting by /100).
    """
    fmt = fmt or PcmFormat()
    _write_wav(path, fmt, default_sounder_samples(fmt, volume=volume))
    return path


def sounder_duration_ms(fmt: PcmFormat) -> int:
    """Length of the default chime in ms, for chapter-offset accounting."""
    return len(default_sounder_samples(fmt)) * 1000 // fmt.sample_rate


def default_sound_path() -> Path | None:
    """Bundled default article-transition sound (a page-turn), or None if absent.

    A short page-turn cue (`quill/assets/audio/page_turn.wav`) is QUILL's default
    boundary sound — more natural than the synthesized chime, which remains the
    last-resort fallback. The asset is conformed to each document's speech format at
    assembly time via :func:`conform_wav_frames`.
    """
    path = Path(__file__).resolve().parents[2] / "assets" / "audio" / "page_turn.wav"
    return path if path.is_file() else None


def _read_wav_mono(path: Path) -> tuple[list[float], int]:
    """Read any PCM WAV (8/16/32-bit, any channels) to mono floats in [-1, 1] + rate.

    Raises :class:`ValueError` for an unsupported sample width so the caller can
    fall back to the generated chime.
    """
    with wave.open(str(path), "rb") as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width == 1:  # unsigned 8-bit, centered at 128
        ints: list[int] = [b - 128 for b in raw]
        peak = 128.0
    elif width == 2:
        ints = list(struct.unpack(f"<{len(raw) // 2}h", raw))
        peak = 32768.0
    elif width == 4:
        ints = list(struct.unpack(f"<{len(raw) // 4}i", raw))
        peak = 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {width} bytes")
    if channels > 1:
        mono = [sum(ints[i : i + channels]) / channels for i in range(0, len(ints), channels)]
    else:
        mono = [float(v) for v in ints]
    return [s / peak for s in mono], rate


def _resample_linear(samples: list[float], src_rate: int, dst_rate: int) -> list[float]:
    """Linear-interpolation resample (good enough for a short earcon; stdlib-only)."""
    if src_rate == dst_rate or not samples:
        return samples
    ratio = dst_rate / src_rate
    n_out = max(0, int(len(samples) * ratio))
    out: list[float] = []
    for i in range(n_out):
        pos = i / ratio
        j = int(pos)
        frac = pos - j
        a = samples[j]
        b = samples[j + 1] if j + 1 < len(samples) else samples[j]
        out.append(a + (b - a) * frac)
    return out


def conform_wav_frames(path: Path, fmt: PcmFormat, *, volume: float = 1.0) -> bytes:
    """Read ``path`` and return raw PCM frames conformed to ``fmt`` (rate/channels/width).

    Resamples, mixes to ``fmt.channels``, and converts to ``fmt.sampwidth``, applying
    ``volume`` (0.0–1.0). This lets any chosen or default boundary sound splice into
    the speech WAVs regardless of its own format. Raises :class:`ValueError` (caught
    upstream) when the source width is unsupported.
    """
    mono, src_rate = _read_wav_mono(path)
    mono = _resample_linear(mono, src_rate, fmt.sample_rate)
    vol = max(0.0, min(1.0, volume))
    peak = _max_amplitude(fmt.sampwidth)
    frames = bytearray()
    for sample in mono:
        value = int(max(-1.0, min(1.0, sample * vol)) * peak)
        if fmt.sampwidth == 2:
            packed = struct.pack("<h", value)
        elif fmt.sampwidth == 4:
            packed = struct.pack("<i", value)
        elif fmt.sampwidth == 1:
            packed = struct.pack("<B", max(0, min(255, value + 128)))
        else:
            raise ValueError(f"Unsupported output sample width: {fmt.sampwidth} bytes")
        frames += packed * fmt.channels
    return bytes(frames)

"""DSP option composition for the Universal Audio Converter (#1255 §6, Advanced).

Advanced mode exposes an optional processing catalog — loudness normalize, gain,
high-pass, trim silence, tempo, compressor, leveler, fades. Every filter here is
one QUILL already builds and tests elsewhere (``core/audio_enhance``,
``core/speech/loudness``, ``core/speech/audio_edit``); this module *composes*
them into the ordered ``-af`` fragment list a :class:`ConversionSpec` carries, so
the converter reuses the tested DSP rather than reinventing it.

Pure and wx-free: the Advanced dialog builds a :class:`DspOptions` from its
checkboxes/spins and calls :func:`build_dsp_filters`; the result becomes
``ConversionSpec.filters`` and flows through ``build_convert_command``'s ``-af``.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.audio_enhance import (
    _COMPRESSOR_FILTER,
    _NIGHT_MODE_FILTER,
    _SMART_SPEED_FILTER,
    _db_to_linear,
)
from quill.core.speech.audio_edit import atempo_filter

# Loudness normalize targets (single-pass loudnorm in the -af graph). The
# two-pass measure->apply ACX method (core/speech/loudness) is more precise; a
# single pass is a good, cheap default for a batch converter (§6 note).
_LOUDNESS_TARGETS: dict[str, str] = {
    "audiobook": "loudnorm=I=-20.0:TP=-3.1:LRA=11.0",  # ACX window
    "podcast": "loudnorm=I=-16.0:TP=-1.5:LRA=11.0",  # streaming/podcast
}

# A rumble high-pass (§6 "High-pass") — same 30 Hz corner audio_enhance uses.
_HIGH_PASS = "highpass=f=30"

# A gentle brickwall limiter to catch peaks after gain/loudness (safety).
_LIMITER = f"alimiter=limit={_db_to_linear(-1.0):.4f}:attack=5:release=50"


@dataclass(frozen=True, slots=True)
class DspOptions:
    """The Advanced processing toggles, all off/neutral by default (§6)."""

    loudness: str = ""  # "" | "audiobook" | "podcast"
    gain_db: float = 0.0
    high_pass: bool = False
    trim_silence: bool = False
    tempo: float = 1.0  # 0.5-2.0 (no pitch change); 1.0 = unchanged
    compressor: bool = False
    leveler: bool = False  # dynaudnorm "night mode"
    fade_in_s: float = 0.0
    fade_out_s: float = 0.0
    limiter: bool = False  # brickwall safety limiter

    def is_active(self) -> bool:
        """True when any option would add a filter (nothing to do otherwise)."""
        return bool(build_dsp_filters(self))


def build_dsp_filters(dsp: DspOptions) -> tuple[str, ...]:
    """Compose *dsp* into an ordered tuple of ``-af`` filter fragments (pure).

    Order is deliberate and stable (mirrors ``audio_enhance.build_filter_graph``):
    clean the signal first (high-pass, trim), shape dynamics (gain, tempo,
    compressor, leveler), normalize loudness, then apply fades last so they act on
    the finished audio. Fade-out uses the reverse-fade-reverse trick so it needs
    no prior duration probe (buffers the stream; fine for a file converter).
    """
    filters: list[str] = []
    if dsp.high_pass:
        filters.append(_HIGH_PASS)
    if dsp.trim_silence:
        filters.append(_SMART_SPEED_FILTER)
    if dsp.gain_db:
        filters.append(f"volume={dsp.gain_db:g}dB")
    if dsp.tempo and abs(dsp.tempo - 1.0) > 1e-6:
        filters.append(atempo_filter(_clamp_tempo(dsp.tempo)))
    if dsp.compressor:
        filters.append(_COMPRESSOR_FILTER)
    if dsp.leveler:
        filters.append(_NIGHT_MODE_FILTER)
    target = _LOUDNESS_TARGETS.get(dsp.loudness.strip().lower())
    if target:
        filters.append(target)
    if dsp.limiter:
        filters.append(_LIMITER)
    if dsp.fade_in_s > 0:
        filters.append(f"afade=t=in:st=0:d={dsp.fade_in_s:g}")
    if dsp.fade_out_s > 0:
        # No total-duration probe: reverse, fade the (now-leading) tail in, reverse
        # back -> an end fade-out. areverse buffers the stream, acceptable here.
        filters.append("areverse")
        filters.append(f"afade=t=in:st=0:d={dsp.fade_out_s:g}")
        filters.append("areverse")
    return tuple(filters)


def _clamp_tempo(tempo: float) -> float:
    """Clamp tempo to atempo's single-stage safe range; the builder chains beyond."""
    return max(0.25, min(4.0, float(tempo)))


def loudness_choices() -> list[tuple[str, str]]:
    """``(value, spoken label)`` pairs for the loudness-normalize choice control."""
    return [
        ("", "No loudness normalization"),
        ("audiobook", "Audiobook / ACX (−20 LUFS)"),
        ("podcast", "Podcast / streaming (−16 LUFS)"),
    ]

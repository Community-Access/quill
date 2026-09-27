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
    "music": "loudnorm=I=-14.0:TP=-1.0:LRA=11.0",  # music streaming services
    "broadcast": "loudnorm=I=-23.0:TP=-1.0:LRA=15.0",  # EBU R128 television/radio
}

# The repair and tone effects added for Quill Converter 1.0.0 (2026-09-27). Each
# is one stock FFmpeg filter with settings chosen for speech first, because
# speech is what most people bring to a converter to fix.
_NOISE_REDUCTION = "afftdn=nr=12:nf=-40:tn=1"  # steady hiss and fan noise
_DEHUM = (
    "bandreject=f=50:width_type=h:w=4,bandreject=f=60:width_type=h:w=4,"
    "bandreject=f=100:width_type=h:w=4,bandreject=f=120:width_type=h:w=4"
)
_DEESSER = "deesser=i=0.4:m=0.5:f=0.5"
_VOICE_CLARITY = "equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=1.2:g=4"
_BASS_BOOST = "bass=g=6:f=100"
_TREBLE_BOOST = "treble=g=4:f=4000"
# Film and TV speech: pull the centre (dialogue) forward, then fold back to
# stereo so every output format can carry it.
_DIALOGUE = "dialoguenhance=original=0.8:enhance=2:voice=4,aformat=channel_layouts=stereo"
_SPEECH_NORMALIZE = "speechnorm=e=6.25:r=0.00001:l=1"

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
    noise_reduction: bool = False
    remove_hum: bool = False  # 50 and 60 Hz mains hum and their first harmonic
    deesser: bool = False
    voice_clarity: bool = False
    bass_boost: bool = False
    treble_boost: bool = False
    dialogue_boost: bool = False
    speech_normalize: bool = False  # fast per-phrase leveling for speech

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
    if dsp.remove_hum:
        filters.append(_DEHUM)
    if dsp.noise_reduction:
        filters.append(_NOISE_REDUCTION)
    if dsp.trim_silence:
        filters.append(_SMART_SPEED_FILTER)
    if dsp.gain_db:
        filters.append(f"volume={dsp.gain_db:g}dB")
    if dsp.tempo and abs(dsp.tempo - 1.0) > 1e-6:
        filters.append(atempo_filter(_clamp_tempo(dsp.tempo)))
    if dsp.deesser:
        filters.append(_DEESSER)
    if dsp.voice_clarity:
        filters.append(_VOICE_CLARITY)
    if dsp.bass_boost:
        filters.append(_BASS_BOOST)
    if dsp.treble_boost:
        filters.append(_TREBLE_BOOST)
    if dsp.dialogue_boost:
        filters.append(_DIALOGUE)
    if dsp.compressor:
        filters.append(_COMPRESSOR_FILTER)
    if dsp.speech_normalize:
        filters.append(_SPEECH_NORMALIZE)
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
        ("music", "Music streaming (−14 LUFS)"),
        ("broadcast", "Broadcast TV and radio, EBU R128 (−23 LUFS)"),
    ]

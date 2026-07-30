"""One-click conversion presets for the Universal Audio Converter (#1255 §7).

A preset is a named :class:`~quill.core.audio.convert.ConversionSpec` that sets
format + sensible options together, so Basic mode reaches a good result in one
choice. Each is a *starting point* Advanced mode can override, and a user's
Advanced recipe can be saved back as a new preset ("Save as preset…").

Pure and wx-free: the dialog reads :data:`BUILTIN_PRESETS` for its choice list
and calls :func:`preset_spec` to resolve a selection into a spec. The rich
two-pass loudness / compression DSP presets (§6) land with v2; the v1 built-ins
here set format, channels, bitrate/VBR and sample rate, plus the single-pass
filters (e.g. a rumble high-pass) the command builder already composes via -af.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.audio.convert import Channels, ConversionSpec

# A gentle rumble high-pass, safe to apply single-pass (§6 "High-pass (rumble)").
_RUMBLE_HIGHPASS = "highpass=f=30"


@dataclass(frozen=True, slots=True)
class Preset:
    """A named, one-click conversion recipe."""

    id: str
    name: str  # shown in the preset choice (spoken on focus)
    description: str  # a plain-language "what this is good for"
    spec: ConversionSpec


BUILTIN_PRESETS: tuple[Preset, ...] = (
    Preset(
        id="just_convert",
        name="Just convert (no processing)",
        description="Pure format change — no loudness, channel or rate changes.",
        spec=ConversionSpec(fmt="mp3"),
    ),
    Preset(
        id="mp3_320",
        name="MP3 320 kbps (maximum quality)",
        description="High-bitrate MP3; the most compatible high-quality choice.",
        spec=ConversionSpec(fmt="mp3", bitrate_kbps=320),
    ),
    Preset(
        id="mp3_192",
        name="MP3 192 kbps",
        description="A good balance of quality and file size.",
        spec=ConversionSpec(fmt="mp3", bitrate_kbps=192),
    ),
    Preset(
        id="mp3_128",
        name="MP3 128 kbps (small)",
        description="Smaller MP3s for quick sharing.",
        spec=ConversionSpec(fmt="mp3", bitrate_kbps=128),
    ),
    Preset(
        id="podcast",
        name="Podcast (MP3, spoken word)",
        description="Mono MP3 for talk audio, with a rumble high-pass.",
        spec=ConversionSpec(
            fmt="mp3", bitrate_kbps=128, channels=Channels.MONO, filters=(_RUMBLE_HIGHPASS,)
        ),
    ),
    Preset(
        id="audiobook",
        name="Audiobook (M4B)",
        description="Mono M4B audiobook container at a compact bitrate.",
        spec=ConversionSpec(fmt="m4b", bitrate_kbps=96, channels=Channels.MONO),
    ),
    Preset(
        id="voice_memo",
        name="Voice memo (small MP3)",
        description="Mono, 22 kHz MP3 — tiny files for spoken notes.",
        spec=ConversionSpec(fmt="mp3", bitrate_kbps=96, channels=Channels.MONO, sample_rate=22050),
    ),
    Preset(
        id="web_opus",
        name="Web voice (Opus)",
        description="Mono Opus at a low bitrate — smallest for the web.",
        spec=ConversionSpec(fmt="opus", bitrate_kbps=48, channels=Channels.MONO, sample_rate=48000),
    ),
    Preset(
        id="archival_flac",
        name="Archival (FLAC, lossless)",
        description="Lossless FLAC; keeps the original rate and channels.",
        spec=ConversionSpec(fmt="flac"),
    ),
    Preset(
        id="hearing_aid_mono",
        name="Hearing-aid mono",
        description="Downmix to a single mono channel for a hearing aid.",
        spec=ConversionSpec(fmt="mp3", bitrate_kbps=128, channels=Channels.MONO),
    ),
)

#: The preset selected by default in Basic mode (a safe, no-surprises choice).
DEFAULT_PRESET_ID = "just_convert"

_BY_ID: dict[str, Preset] = {p.id: p for p in BUILTIN_PRESETS}


def preset_by_id(preset_id: str) -> Preset | None:
    """Look up a built-in preset by id, or ``None`` if unknown."""
    return _BY_ID.get(preset_id.strip().lower())


def preset_spec(preset_id: str) -> ConversionSpec:
    """Resolve a preset id to its :class:`ConversionSpec` (default if unknown)."""
    found = preset_by_id(preset_id)
    if found is not None:
        return found.spec
    return _BY_ID[DEFAULT_PRESET_ID].spec


def preset_choices() -> list[tuple[str, str]]:
    """``(id, spoken_label)`` pairs for the preset choice control, in order.

    The label carries the plain-language description so a screen reader announces
    the trade-off on focus (mirroring the guided-speech engine picker).
    """
    return [(p.id, f"{p.name} — {p.description}") for p in BUILTIN_PRESETS]

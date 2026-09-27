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
from quill.core.audio.formats import VideoQuality

# A gentle rumble high-pass, safe to apply single-pass (§6 "High-pass (rumble)").
_RUMBLE_HIGHPASS = "highpass=f=30"


@dataclass(frozen=True, slots=True)
class Preset:
    """A named, one-click conversion recipe."""

    id: str
    name: str  # shown in the preset choice (spoken on focus)
    description: str  # a plain-language "what this is good for"
    spec: ConversionSpec
    # "audio" presets shape a sound file; "video" presets shape a video file's
    # picture (its sound follows the format's own audio codec and the effects).
    kind: str = "audio"


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

#: Presets for the video output formats (Quill Converter 1.0.0). Named for the
#: result, never for a codec setting: "up to 720p" rather than "CRF 28".
VIDEO_PRESETS: tuple[Preset, ...] = (
    Preset(
        id="video_same",
        name="Same quality (recommended)",
        description="Looks the same as the original, at the original size.",
        spec=ConversionSpec(fmt="mp4", video_quality=VideoQuality.HIGH),
        kind="video",
    ),
    Preset(
        id="video_web",
        name="Phones and the web, up to 1080p",
        description="Good quality in a noticeably smaller file.",
        spec=ConversionSpec(fmt="mp4", video_quality=VideoQuality.BALANCED, video_max_height=1080),
        kind="video",
    ),
    Preset(
        id="video_small",
        name="Smaller file, up to 720p",
        description="For sharing and messaging; about a quarter of the size.",
        spec=ConversionSpec(fmt="mp4", video_quality=VideoQuality.SMALL, video_max_height=720),
        kind="video",
    ),
    Preset(
        id="video_tiny",
        name="Smallest file, up to 480p",
        description="For slow connections and small screens.",
        spec=ConversionSpec(fmt="mp4", video_quality=VideoQuality.SMALL, video_max_height=480),
        kind="video",
    ),
    Preset(
        id="video_remux",
        name="Change the container only (fastest, no quality loss)",
        description="Copies picture and sound untouched into the new format. "
        "Effects cannot apply, and some combinations do not fit every container.",
        spec=ConversionSpec(fmt="mp4", copy_video=True),
        kind="video",
    ),
)

#: The video preset selected when a video format is first chosen.
DEFAULT_VIDEO_PRESET_ID = "video_same"

#: The preset selected by default in Basic mode (a safe, no-surprises choice).
DEFAULT_PRESET_ID = "just_convert"

_BY_ID: dict[str, Preset] = {p.id: p for p in BUILTIN_PRESETS + VIDEO_PRESETS}


def preset_by_id(preset_id: str) -> Preset | None:
    """Look up a built-in preset by id, or ``None`` if unknown."""
    return _BY_ID.get(preset_id.strip().lower())


def preset_spec(preset_id: str) -> ConversionSpec:
    """Resolve a preset id to its :class:`ConversionSpec` (default if unknown)."""
    found = preset_by_id(preset_id)
    if found is not None:
        return found.spec
    return _BY_ID[DEFAULT_PRESET_ID].spec


def preset_choices(kind: str = "audio") -> list[tuple[str, str]]:
    """``(id, spoken_label)`` pairs for the preset choice control, in order.

    The label carries the plain-language description so a screen reader announces
    the trade-off on focus (mirroring the guided-speech engine picker). *kind*
    picks the audio presets (the default, and all Audio Studio ever shows) or
    the video ones.
    """
    pool = VIDEO_PRESETS if kind == "video" else BUILTIN_PRESETS
    return [(p.id, f"{p.name} — {p.description}") for p in pool]

"""The Universal Converter's format catalogue: what it reads, what it writes.

Extracted from :mod:`quill.core.audio.convert` (GATE-11: extract, never
rebaseline) when Quill Converter 1.0.0 widened the matrix on 2026-09-27. One
table per question, so "can it read .mts?" and "what does AMR force?" each
have exactly one place to be answered:

* **Inputs** -- :data:`AUDIO_EXTENSIONS` and :data:`VIDEO_EXTENSIONS`. Every
  entry is something the bundled FFmpeg decodes; a mislabeled or corrupt file
  still fails its own job alone, because each file is probed by the encode.
* **Audio outputs** -- :data:`AUDIO_OUTPUT_FORMATS`, ``(codec, extra, muxer)``
  like the speech ``ENCODE_FORMATS`` they extend.
* **Video outputs** -- :data:`VIDEO_OUTPUT_FORMATS`, one
  :class:`VideoProfile` each, with the quality ladder in
  :func:`video_quality_args`.
* **The constraints a format imposes** -- the sample rates it accepts, the
  channel count it forces, whether a bit rate means anything to it. Before
  these existed a preset could ask AC-3 for 22 kHz or AMR for stereo, and the
  file failed half-way through a batch instead of simply being made right.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from quill.core.speech.ffmpeg import ENCODE_FORMATS

# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #

#: Audio containers and raw streams discovered by extension for a folder add.
AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    # The everyday ones.
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".oga",
    ".opus",
    ".m4a",
    ".m4b",
    ".aac",
    ".wma",
    ".aiff",
    ".aif",
    ".aifc",
    ".alac",
    ".caf",
    ".mka",
    ".weba",
    ".m4r",
    # Lossless and archival.
    ".ape",
    ".wv",
    ".tta",
    ".tak",
    ".shn",
    ".w64",
    ".rf64",
    ".bwf",
    ".dsf",
    ".dff",
    # Film and broadcast audio.
    ".ac3",
    ".eac3",
    ".ec3",
    ".dts",
    ".thd",
    ".mlp",
    ".mp2",
    ".mp1",
    ".mpa",
    # Phones, voice and telephony.
    ".amr",
    ".awb",
    ".spx",
    ".gsm",
    ".au",
    ".snd",
    ".voc",
    # Older and specialist.
    ".mpc",
    ".ra",
    ".oma",
    ".aa3",
    # Tracker music (rendered by libopenmpt).
    ".mod",
    ".xm",
    ".it",
    ".s3m",
})

#: Video containers: their audio can be extracted, and they can be converted
#: to another video format.
VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4",
    ".m4v",
    ".mkv",
    ".mov",
    ".qt",
    ".webm",
    ".avi",
    ".divx",
    ".flv",
    ".f4v",
    ".wmv",
    ".asf",
    ".mpg",
    ".mpeg",
    ".mpe",
    ".vob",
    ".ts",
    ".mts",
    ".m2ts",
    ".m2t",
    ".3gp",
    ".3g2",
    ".ogv",
    ".rm",
    ".rmvb",
    ".mxf",
    ".dv",
    ".wtv",
    ".dvr-ms",
    ".nut",
})

#: Every input extension the converter recognizes for a folder scan.
INPUT_EXTENSIONS: frozenset[str] = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def open_wildcard() -> str:
    """The Add Files dialog's wildcard, generated so it cannot drift from the sets."""

    def patterns(exts: frozenset[str]) -> str:
        return ";".join(f"*{ext}" for ext in sorted(exts))

    return (
        f"Audio and video files|{patterns(INPUT_EXTENSIONS)}"
        f"|Audio files|{patterns(AUDIO_EXTENSIONS)}"
        f"|Video files|{patterns(VIDEO_EXTENSIONS)}"
        "|All files (*.*)|*.*"
    )


# --------------------------------------------------------------------------- #
# Audio outputs
# --------------------------------------------------------------------------- #

#: Output formats beyond the speech ENCODE_FORMATS, each ``(codec, default
#: extra args, muxer)``. PCM codecs are replaced by the bit-depth table below.
EXTRA_ENCODE_FORMATS: dict[str, tuple[str, list[str], str]] = {
    "wav": ("pcm_s16le", [], ""),
    "aac": ("aac", ["-b:a", "192k"], "adts"),
    "aiff": ("pcm_s16be", [], "aiff"),
    "alac": ("alac", [], "ipod"),
    "wma": ("wmav2", ["-b:a", "192k"], "asf"),
    "caf": ("pcm_s16le", [], "caf"),
    "ac3": ("ac3", ["-b:a", "384k"], "ac3"),
    "eac3": ("eac3", ["-b:a", "384k"], "eac3"),
    "mp2": ("mp2", ["-b:a", "192k"], "mp2"),
    "wv": ("wavpack", [], "wv"),
    "tta": ("tta", [], "tta"),
    "mka": ("flac", [], "matroska"),
    "weba": ("libopus", ["-b:a", "128k"], "webm"),
    "m4r": ("aac", ["-b:a", "256k"], "ipod"),
    "spx": ("libspeex", [], "ogg"),
    "amr": ("libopencore_amrnb", ["-b:a", "12.2k"], "amr"),
    "awb": ("libvo_amrwbenc", ["-b:a", "23.85k"], "amr"),
    "au": ("pcm_s16be", [], "au"),
    "w64": ("pcm_s16le", [], "w64"),
}

#: Every audio output format id (subject to the runtime encoder probe).
AUDIO_OUTPUT_FORMATS: dict[str, tuple[str, list[str], str]] = {
    **ENCODE_FORMATS,
    **EXTRA_ENCODE_FORMATS,
}

#: PCM formats pick their concrete codec from the bit depth. ``None`` is the
#: format's default. WAV and W64 offer real 32-bit float, because that is what
#: the Advanced dialog's "32-bit float" says.
PCM_CODECS: dict[str, dict[int | None, str]] = {
    "wav": {None: "pcm_s16le", 16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_f32le"},
    "w64": {None: "pcm_s16le", 16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_f32le"},
    "caf": {None: "pcm_s16le", 16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_f32le"},
    # AIFF and Sun AU are big-endian formats: a little-endian codec is refused
    # by their muxers ("codec not currently supported in container").
    "aiff": {None: "pcm_s16be", 16: "pcm_s16be", 24: "pcm_s24be", 32: "pcm_s32be"},
    "au": {None: "pcm_s16be", 16: "pcm_s16be", 24: "pcm_s24be", 32: "pcm_s32be"},
}

#: Lossless or uncompressed formats: a bit rate means nothing to them.
LOSSLESS_FORMATS: frozenset[str] = frozenset({
    "wav",
    "flac",
    "aiff",
    "alac",
    "caf",
    "wv",
    "tta",
    "mka",
    "au",
    "w64",
})

#: Formats whose bit rate is fixed by the codec itself (AMR's modes).
FIXED_BITRATE_FORMATS: frozenset[str] = frozenset({"amr", "awb"})

#: The sample rates a format accepts. A requested rate outside the list is
#: moved to the nearest one it accepts rather than failing the file.
ALLOWED_SAMPLE_RATES: dict[str, tuple[int, ...]] = {
    "ac3": (48000, 44100, 32000),
    "eac3": (48000, 44100, 32000),
    # MPEG-1 rates only: at the MPEG-2 "half" rates (24/22.05/16 kHz) the
    # encoder refuses any bit rate above 160 kbps, so a 22 kHz voice memo
    # failed at the default 192k. DVD and broadcast MP2 is 48 kHz anyway.
    "mp2": (48000, 44100, 32000),
    "opus": (48000, 24000, 16000, 12000, 8000),
    "weba": (48000, 24000, 16000, 12000, 8000),
    "spx": (32000, 16000, 8000),
    "amr": (8000,),
    "awb": (16000,),
}

#: Formats whose encoder accepts rates it cannot then encode at the default
#: bit rate, so the rate is always set rather than left to the source.
_ALWAYS_SET_RATE: frozenset[str] = frozenset({"mp2"})

#: Formats that only carry one channel.
MONO_ONLY_FORMATS: frozenset[str] = frozenset({"amr", "awb"})

#: Output file extension per format id where it is not simply ``.<id>``.
OUTPUT_EXTENSION: dict[str, str] = {
    "alac": ".m4a",
    "mp4_hevc": ".mp4",
}


def output_extension(fmt: str) -> str:
    """The file extension (with dot) for a format id."""
    key = fmt.strip().lower()
    return OUTPUT_EXTENSION.get(key, "." + key)


def fit_sample_rate(fmt: str, rate: int | None) -> int | None:
    """*rate* moved to the nearest rate *fmt* accepts; forced for fixed-rate codecs."""
    key = fmt.strip().lower()
    allowed = ALLOWED_SAMPLE_RATES.get(key)
    if not allowed:
        return rate
    if rate is None:
        return allowed[0] if len(allowed) == 1 or key in _ALWAYS_SET_RATE else None
    return min(allowed, key=lambda candidate: abs(candidate - rate))


# --------------------------------------------------------------------------- #
# Video outputs
# --------------------------------------------------------------------------- #


class VideoQuality(StrEnum):
    """How hard a video encode works to keep detail (plain words, not CRF)."""

    HIGH = "high"  # visually the same as the source
    BALANCED = "balanced"  # good for phones and the web
    SMALL = "small"  # smallest file that still looks fine


@dataclass(frozen=True, slots=True)
class VideoProfile:
    """One video output format: its video and audio codecs and its container."""

    video_codec: str
    audio_codec: str
    audio_args: tuple[str, ...]
    muxer: str
    video_args: tuple[str, ...] = ()
    # Keep every audio track (a described-audio track, a second language) --
    # only where the container carries more than one reliably.
    all_audio_tracks: bool = True
    # Copy subtitle / caption tracks through untouched (Matroska only: it
    # takes any subtitle codec, where MP4 refuses the bitmap kinds).
    keep_subtitles: bool = False


_EVEN = "scale='trunc(iw/2)*2':'trunc(ih/2)*2'"  # x264/x265 refuse odd sizes

VIDEO_OUTPUT_FORMATS: dict[str, VideoProfile] = {
    "mp4": VideoProfile(
        "libx264",
        "aac",
        ("-b:a", "160k"),
        "mp4",
        ("-pix_fmt", "yuv420p", "-movflags", "+faststart"),
    ),
    "mp4_hevc": VideoProfile(
        "libx265",
        "aac",
        ("-b:a", "160k"),
        "mp4",
        ("-pix_fmt", "yuv420p", "-tag:v", "hvc1", "-movflags", "+faststart"),
    ),
    "mkv": VideoProfile(
        "libx264",
        "aac",
        ("-b:a", "160k"),
        "matroska",
        ("-pix_fmt", "yuv420p"),
        keep_subtitles=True,
    ),
    "webm": VideoProfile(
        "libvpx-vp9",
        "libopus",
        ("-b:a", "128k"),
        "webm",
        ("-pix_fmt", "yuv420p", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4"),
    ),
    "mov": VideoProfile(
        "libx264",
        "aac",
        ("-b:a", "160k"),
        "mov",
        ("-pix_fmt", "yuv420p"),
    ),
    "avi": VideoProfile(
        "libxvid",
        "libmp3lame",
        ("-b:a", "192k"),
        "avi",
        ("-pix_fmt", "yuv420p"),
        all_audio_tracks=False,
    ),
    "wmv": VideoProfile("wmv2", "wmav2", ("-b:a", "192k"), "asf", all_audio_tracks=False),
    "mpg": VideoProfile(
        "mpeg2video",
        "mp2",
        ("-b:a", "192k"),
        "mpeg",
        ("-pix_fmt", "yuv420p"),
        all_audio_tracks=False,
    ),
    "ogv": VideoProfile(
        "libtheora",
        "libvorbis",
        ("-q:a", "5"),
        "ogg",
        all_audio_tracks=False,
    ),
}

_QUALITY_LADDER: dict[str, tuple[str, dict[VideoQuality, str]]] = {
    "libx264": (
        "-crf",
        {VideoQuality.HIGH: "18", VideoQuality.BALANCED: "23", VideoQuality.SMALL: "28"},
    ),
    "libx265": (
        "-crf",
        {VideoQuality.HIGH: "22", VideoQuality.BALANCED: "28", VideoQuality.SMALL: "32"},
    ),
    "libvpx-vp9": (
        "-crf",
        {VideoQuality.HIGH: "28", VideoQuality.BALANCED: "34", VideoQuality.SMALL: "40"},
    ),
    "libxvid": (
        "-q:v",
        {VideoQuality.HIGH: "3", VideoQuality.BALANCED: "5", VideoQuality.SMALL: "8"},
    ),
    "mpeg2video": (
        "-q:v",
        {VideoQuality.HIGH: "3", VideoQuality.BALANCED: "5", VideoQuality.SMALL: "8"},
    ),
    "wmv2": ("-q:v", {VideoQuality.HIGH: "3", VideoQuality.BALANCED: "5", VideoQuality.SMALL: "8"}),
    "libtheora": (
        "-q:v",
        {VideoQuality.HIGH: "9", VideoQuality.BALANCED: "7", VideoQuality.SMALL: "5"},
    ),
}


def video_quality_args(video_codec: str, quality: VideoQuality) -> list[str]:
    """The rate-control switches for *video_codec* at *quality* (pure)."""
    rung = _QUALITY_LADDER.get(video_codec)
    if rung is None:
        return []
    flag, values = rung
    args = [flag, values[quality]]
    if video_codec == "libvpx-vp9":
        args += ["-b:v", "0"]  # constant quality needs the bit-rate cap off
    if video_codec in ("libx264", "libx265"):
        args += ["-preset", "medium"]
    return args


def video_scale_filter(video_codec: str, max_height: int | None) -> str:
    """The ``-vf`` scale for a height cap, always leaving even dimensions."""
    if max_height:
        return f"scale=-2:'trunc(min({int(max_height)},ih)/2)*2'"
    if video_codec in ("libx264", "libx265", "libxvid", "mpeg2video", "libvpx-vp9"):
        return _EVEN
    return ""


def is_video_format(fmt: str) -> bool:
    """True when *fmt* writes a video file rather than an audio one."""
    return fmt.strip().lower() in VIDEO_OUTPUT_FORMATS


def required_encoders(fmt: str) -> tuple[str, ...]:
    """The ffmpeg encoder names *fmt* needs (empty when always available)."""
    key = fmt.strip().lower()
    video = VIDEO_OUTPUT_FORMATS.get(key)
    if video is not None:
        return (video.video_codec, video.audio_codec)
    if key in PCM_CODECS:
        return ()
    profile = AUDIO_OUTPUT_FORMATS.get(key)
    return (profile[0],) if profile else ()


# --------------------------------------------------------------------------- #
# The encoder probe's parser
# --------------------------------------------------------------------------- #


def parse_encoder_names(encoders_output: str) -> frozenset[str]:
    """Parse ``ffmpeg -encoders`` output into a set of encoder names (pure).

    Each listed line looks like `` A..... libmp3lame  MP3 (MPEG audio layer 3)``:
    a flags column, the encoder name, then a description. We take the second
    whitespace token of any line whose first token is all flag characters.
    """
    names: set[str] = set()
    past_legend = False
    for raw in encoders_output.splitlines():
        line = raw.strip()
        if line and set(line) <= {"-"}:
            # The ``------`` rule separates the flag legend from the real list.
            past_legend = True
            continue
        if not past_legend or not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        flags, name = parts[0], parts[1]
        # A real encoder line: a >=2-char flag column whose first char is the
        # stream type (V/A/S), and an identifier name (skips the '= Audio' legend).
        if len(flags) >= 2 and flags[0] in "VAS" and all(c in ".VASFXBDEILT" for c in flags):
            if name[:1].isalnum():
                names.add(name)
    return frozenset(names)


# --------------------------------------------------------------------------- #
# Names people read
# --------------------------------------------------------------------------- #

#: Output formats in the order the chooser offers them: the everyday ones
#: first, then the specialist, then video.
OUTPUT_ORDER: tuple[str, ...] = (
    "mp3",
    "m4a",
    "m4b",
    "opus",
    "ogg",
    "flac",
    "wav",
    "aac",
    "aiff",
    "alac",
    "wma",
    "caf",
    "ac3",
    "eac3",
    "mp2",
    "wv",
    "tta",
    "mka",
    "weba",
    "m4r",
    "spx",
    "amr",
    "awb",
    "au",
    "w64",
    "mp4",
    "mp4_hevc",
    "mkv",
    "webm",
    "mov",
    "avi",
    "wmv",
    "mpg",
    "ogv",
)

#: Plain-language labels: what the format is, and when you would want it.
FORMAT_LABELS: dict[str, str] = {
    "mp3": "MP3 audio -- plays everywhere",
    "m4a": "M4A audio (AAC) -- Apple devices and phones",
    "m4b": "M4B audiobook -- remembers your place in book players",
    "opus": "Opus audio -- smallest files for speech",
    "ogg": "Ogg Vorbis audio -- open format",
    "flac": "FLAC -- lossless, smaller than WAV",
    "wav": "WAV -- uncompressed, for editing",
    "aac": "AAC audio stream (.aac)",
    "aiff": "AIFF -- uncompressed, Apple",
    "alac": "Apple Lossless (ALAC, .m4a)",
    "wma": "WMA -- Windows Media Audio",
    "caf": "CAF -- Core Audio Format",
    "ac3": "AC-3 (Dolby Digital) -- DVD and home theater",
    "eac3": "E-AC-3 (Dolby Digital Plus)",
    "mp2": "MP2 -- broadcast and DVD audio",
    "wv": "WavPack -- lossless",
    "tta": "TTA (True Audio) -- lossless",
    "mka": "MKA -- Matroska audio, lossless FLAC inside",
    "weba": "WebM audio (Opus) -- for web pages",
    "m4r": "M4R -- iPhone ringtone",
    "spx": "Speex -- low bit rate speech",
    "amr": "AMR narrowband -- phone voice memos",
    "awb": "AMR wideband -- clearer phone voice",
    "au": "AU -- Sun and Java audio",
    "w64": "Wave64 -- WAV for files over 4 GB",
    "mp4": "MP4 video (H.264) -- plays everywhere",
    "mp4_hevc": "MP4 video (H.265, HEVC) -- half the size, newer devices",
    "mkv": "MKV video (H.264) -- keeps every audio and subtitle track",
    "webm": "WebM video (VP9) -- for the web",
    "mov": "MOV video (H.264) -- QuickTime and Apple editing",
    "avi": "AVI video (Xvid) -- older players and TVs",
    "wmv": "WMV video -- Windows Media",
    "mpg": "MPEG-2 video -- DVD players",
    "ogv": "Ogg video (Theora) -- open format",
}


def format_label(fmt: str) -> str:
    """The chooser label for a format id (falls back to the id in capitals)."""
    key = fmt.strip().lower()
    return FORMAT_LABELS.get(key, key.upper())

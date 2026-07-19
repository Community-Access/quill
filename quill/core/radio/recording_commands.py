"""Pure ffmpeg/ffprobe command + filename builders for radio recording.

Extracted from :mod:`quill.core.radio.recording` (GATE-11 decomposition) so the
recorder module stays focused on the :class:`~quill.core.radio.recording.RadioRecorder`
lifecycle. Everything here is pure and wx-free: no process is launched, no state
is held. :mod:`quill.core.radio.recording` re-exports the public names, so
``from quill.core.radio.recording import build_record_command`` keeps working.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

#: Formats a live stream can be recorded to. The first four re-encode the
#: decoded audio to a chosen codec. ``"copy"`` is the raw-capture mode
#: (feature request): ffmpeg stream-copies the server's audio packets with no
#: re-encoding, so the saved file is bit-for-bit the original stream -- the
#: most lossless capture possible, for a listener who wants to edit/convert it
#: themselves. All are streamable containers (no trailing index atom like
#: MP4/M4A), so even an unclean stop leaves a playable file up to the last
#: flushed frame.
RECORD_FORMATS = ("mp3", "ogg", "flac", "wav", "copy")
#: Human labels for the Recording Settings format dropdown.
RECORD_FORMAT_LABELS: dict[str, str] = {
    "mp3": "MP3",
    "ogg": "OGG Vorbis",
    "flac": "FLAC (lossless, re-encoded)",
    "wav": "WAV (lossless, re-encoded)",
    "copy": "Raw stream -- exactly as sent, no re-encoding (lossless)",
}
_CODECS = {"mp3": "libmp3lame", "ogg": "libvorbis", "flac": "flac", "wav": "pcm_s16le"}

#: Formats that re-encode to a lossy codec, so the chosen bitrate matters.
#: Lossless re-encodes (flac/wav) and the raw stream copy ignore it entirely
#: (see ``build_record_command``: ``-b:a`` is only emitted for these).
BITRATE_FORMATS = ("mp3", "ogg")


def format_uses_bitrate(format: str) -> bool:
    """Whether a recording *format* honours the bitrate setting (pure).

    False for the raw stream copy and the lossless re-encodes, so the Recording
    Settings dialog can hide the bitrate control when it would do nothing
    (#1155 -- a bitrate box under Raw stream is confusing UX).
    """
    return format in BITRATE_FORMATS


#: The raw-capture container extension for a probed source codec. Common codecs
#: get their natural elementary-stream extension so the file opens anywhere;
#: anything else falls back to Matroska audio (``.mka``), which stream-copies
#: any codec losslessly into one file the user can extract from later.
_RAW_EXT_BY_CODEC: dict[str, str] = {
    "mp3": "mp3",
    "aac": "aac",
    "aac_latm": "aac",
    "vorbis": "ogg",
    "opus": "opus",
    "flac": "flac",
    "alac": "m4a",
    "ac3": "ac3",
    "wav": "wav",
    "pcm_s16le": "wav",
}
#: Universal lossless fallback container for stream-copy of an unknown codec.
_RAW_FALLBACK_EXT = "mka"

#: ffmpeg ``-loglevel`` values Quill Radio will pass through (quill-radio #5);
#: anything else falls back to ``"error"``. Debug mode uses ``"verbose"``.
_FFMPEG_LOGLEVELS = frozenset({"quiet", "error", "warning", "info", "verbose", "debug"})


def _sanitize_filename_component(text: str) -> str:
    """Strip characters that are invalid in a filename on any of QUILL's
    supported platforms, collapsing whitespace runs to one space."""
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def build_filename(pattern: str, *, station: str, when: datetime) -> str:
    """Fill in ``{station}``/``{date}``/``{time}`` tokens, then sanitize the
    result for use as a filename (without extension)."""
    filled = (
        pattern
        .replace("{station}", station)
        .replace("{date}", when.strftime("%Y-%m-%d"))
        .replace("{time}", when.strftime("%H-%M-%S"))
    )
    sanitized = _sanitize_filename_component(filled)
    return sanitized or "recording"


def uniquify(path: Path) -> Path:
    """Return a path that does not yet exist, appending ``" (2)"``, ``" (3)"``
    before the extension (R4/13.2). Replaces the old unconditional ``-y``
    overwrite, so a user pattern without ``{time}`` no longer silently destroys
    an earlier recording of the same name."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for n in range(2, 1000):
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
    # Pathological fallback (999 same-name files): keep the original; -y is gone
    # so ffmpeg would refuse to overwrite, but we never expect to reach here.
    return path


def build_record_command(
    ffmpeg: str,
    stream_url: str,
    out_path: Path,
    *,
    format: str,
    bitrate_kbps: int,
    duration_seconds: int,
    reconnect_delay_max: int = 0,
    filter_graph: str = "",
    user_agent: str = "",
    loglevel: str = "error",
) -> list[str]:
    """Build the ffmpeg argv that records *stream_url* to *out_path*.

    Pure and unit-tested. ``-t`` caps every recording at ``duration_seconds``
    even if :meth:`RadioRecorder.stop` is never called, so a forgotten
    recording cannot grow unbounded. A positive ``reconnect_delay_max`` turns
    on ffmpeg's own HTTP reconnect handling (first line of defense against a
    dropped connection; the recorder's process-level retry is the second),
    valid only for http(s) inputs. A non-empty ``filter_graph`` (built by
    ``core.audio_enhance.build_filter_graph``, this module stays decoupled
    from that one) records the *filtered* audio -- Sound Enhancements applied
    to the archival copy, not just live playback.

    ``format="copy"`` is the raw-capture mode: ffmpeg stream-copies the
    server's audio packets (``-c:a copy``) with no decode/re-encode, so the
    file is bit-for-bit the original. A bitrate and a filter graph are
    meaningless with no re-encode and are ignored (Sound Enhancements cannot
    apply to a raw copy). The output container is chosen by ``out_path``'s
    extension, which the caller resolves from the stream's own codec.

    ``loglevel`` sets ffmpeg's own ``-loglevel`` (quill-radio #5). The default
    ``"error"`` keeps the captured stderr quiet; debug mode passes ``"verbose"``
    so the recording's connection and codec decisions land in ``quill.log``. An
    unrecognized value falls back to ``"error"``.
    """
    level = loglevel if loglevel in _FFMPEG_LOGLEVELS else "error"
    args = [ffmpeg, "-hide_banner", "-loglevel", level]
    is_http = stream_url.lower().startswith(("http://", "https://"))
    if user_agent and is_http:
        # Identify as Quill Radio in the station's listener logs instead of the
        # default "Lavf" (quill-radio #6). Input option, so it goes before -i.
        args.extend(["-user_agent", user_agent])
    if reconnect_delay_max > 0 and stream_url.lower().startswith(("http://", "https://")):
        args.extend([
            "-reconnect",
            "1",
            "-reconnect_streamed",
            "1",
            "-reconnect_delay_max",
            str(reconnect_delay_max),
        ])
    args.extend(["-i", stream_url, "-vn"])
    if format == "copy":
        # Raw capture: copy packets verbatim -- no filter (nothing is decoded),
        # no bitrate (no re-encode).
        args.extend(["-c:a", "copy"])
    else:
        if filter_graph:
            args.extend(["-af", filter_graph])
        args.extend(["-c:a", _CODECS.get(format, "libmp3lame")])
        if format in ("mp3", "ogg"):
            args.extend(["-b:a", f"{max(32, bitrate_kbps)}k"])
    args.extend(["-t", str(max(1, duration_seconds)), str(out_path)])
    return args


def build_probe_codec_command(ffprobe: str, stream_url: str, *, user_agent: str = "") -> list[str]:
    """ffprobe argv that prints the first audio stream's codec name (pure).

    Raw-capture mode uses this to pick a natural output extension for the
    server's actual codec; a probe failure just falls back to Matroska. A
    non-empty ``user_agent`` identifies the probe as Quill Radio on http(s)
    inputs (quill-radio #6).
    """
    args = [ffprobe]
    if user_agent and stream_url.lower().startswith(("http://", "https://")):
        args.extend(["-user_agent", user_agent])
    args.extend([
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        stream_url,
    ])
    return args


def parse_probe_codec(output: str) -> str:
    """The codec name from ``build_probe_codec_command`` output (pure)."""
    for line in output.splitlines():
        name = line.strip()
        if name:
            return name.lower()
    return ""


def raw_capture_extension(codec: str) -> str:
    """The lossless container extension for a raw stream-copy of *codec* (pure).

    Common codecs get their natural extension; anything else falls back to
    Matroska audio (``.mka``), which stream-copies any codec losslessly.
    """
    return _RAW_EXT_BY_CODEC.get(codec.strip().lower(), _RAW_FALLBACK_EXT)

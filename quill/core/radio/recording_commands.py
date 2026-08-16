"""Pure ffmpeg/ffprobe command + filename builders for radio recording.

Extracted from :mod:`quill.core.radio.recording` (GATE-11 decomposition) so the
recorder module stays focused on the :class:`~quill.core.radio.recording.RadioRecorder`
lifecycle. Everything here is pure and wx-free: no process is launched, no state
is held. :mod:`quill.core.radio.recording` re-exports the public names, so
``from quill.core.radio.recording import build_record_command`` keeps working.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from quill.core import http_client
from quill.core.speech.ffmpeg import find_ffprobe
from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

#: How long the raw-capture codec probe may take before it gives up and falls
#: back to the universal container. Short on purpose: this runs on the path to
#: starting a recording, and a slow answer is worse than a safe default.
_PROBE_TIMEOUT_SECONDS = 10.0

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


def encode_args_for_format(format: str, bitrate_kbps: int) -> list[str]:
    """The codec/quality ffmpeg args for a recording *format* (pure).

    One source of truth for "how a recording is encoded", shared by
    :func:`build_record_command` (the capture itself) and the exact-OptiLab
    post-pass (:mod:`quill.core.audio.exact_optilab`), which re-encodes the
    finished file and must land on the same codec and bitrate it was recorded
    with -- otherwise turning exact processing on would silently change the
    format of what somebody keeps.

    ``"copy"`` has no encode args at all: a raw capture is never decoded, so it
    cannot be re-encoded without ceasing to be one. Callers must not post-process
    a raw capture.
    """
    if format == "copy":
        return []
    args = ["-c:a", _CODECS.get(format, "libmp3lame")]
    if format in BITRATE_FORMATS:
        args.extend(["-b:a", f"{max(32, bitrate_kbps)}k"])
    return args


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

#: Default ffmpeg ``-rw_timeout`` for network recordings (#1222): abort a read
#: that stalls this long so a half-open socket can't wedge the recorder. Long
#: enough to ride out ordinary rebuffering, short enough to detect a dead stream
#: promptly and hand off to the reconnect path.
_DEFAULT_RW_TIMEOUT_SECONDS = 30


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


def uniquify(path: Path, reserved: set[Path] | None = None) -> Path:
    """Return a path that does not yet exist, appending ``" (2)"``, ``" (3)"``
    before the extension (R4/13.2). Replaces the old unconditional ``-y``
    overwrite, so a user pattern without ``{time}`` no longer silently destroys
    an earlier recording of the same name.

    ``reserved`` is an optional set of paths that are *about to* be written but do
    not exist on disk yet (a recording still starting up). A path in it is treated
    as taken, so two concurrent same-name recordings resolve to distinct names
    even before either file exists -- closing the check-then-write race."""
    taken = reserved if reserved is not None else set()

    def _free(candidate: Path) -> bool:
        return not candidate.exists() and candidate not in taken

    if _free(path):
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for n in range(2, 1000):
        candidate = parent / f"{stem} ({n}){suffix}"
        if _free(candidate):
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
    rw_timeout_seconds: int = _DEFAULT_RW_TIMEOUT_SECONDS,
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

    ``rw_timeout_seconds`` (#1222) sets ffmpeg's ``-rw_timeout`` I/O read timeout
    for http(s) inputs, so a *stalled* connection -- a half-open socket where the
    stream neither delivers data nor errors -- makes ffmpeg abort and exit
    instead of blocking in ``recv()`` forever. Without it, a dropped network that
    leaves the socket half-open left the recorder wedged: still "recording" but
    advancing nothing, and never reaching the reconnect/finalize path (which only
    runs once ffmpeg exits). A timeout error is transient, so the recorder then
    reconnects (or, with reconnect off, finalizes the partial) -- "continue or
    fail as necessary". ``0`` disables it. It never trips on a healthy stream,
    whose reads complete continuously; only a genuine stall exceeds the window.
    """
    level = loglevel if loglevel in _FFMPEG_LOGLEVELS else "error"
    args = [ffmpeg, "-hide_banner", "-loglevel", level]
    is_http = stream_url.lower().startswith(("http://", "https://"))
    if user_agent and is_http:
        # Identify as Quill Radio in the station's listener logs instead of the
        # default "Lavf" (quill-radio #6). Input option, so it goes before -i.
        args.extend(["-user_agent", user_agent])
    if is_http:
        # Per-host Referer: ccMixter's content host answers 403 without one
        # (stream_headers.referrer_for is the single source of that knowledge).
        from quill.core.radio.stream_headers import referrer_for

        referrer = referrer_for(stream_url)
        if referrer:
            args.extend(["-referer", referrer])
    if is_http and rw_timeout_seconds > 0:
        # -rw_timeout is in MICROSECONDS and applies to the network read, so a
        # silent stall (not just a clean disconnect) is detected and aborted.
        args.extend(["-rw_timeout", str(int(rw_timeout_seconds) * 1_000_000)])
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
        args.extend(encode_args_for_format(format, bitrate_kbps))
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


def probe_capture_extension(stream_url: str) -> str:
    """Probe *stream_url*'s audio codec and return the raw-capture extension.

    Lives here rather than in ``recording.py`` because this is where the
    probe command is built and its output parsed -- the runner belongs with
    the pair it drives, and ``recording.py`` is at its GATE-11 ceiling.

    Best-effort: a missing ffprobe, a probe error, or a timeout all fall back
    to Matroska audio (``.mka``), the universal lossless copy container, so
    raw capture always has a valid destination.
    """
    ffprobe = find_ffprobe()
    if ffprobe is None:
        return raw_capture_extension("")
    extra_kwargs: dict = {}
    if os.name == "nt":
        extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        completed = subprocess.run(
            build_probe_codec_command(ffprobe, stream_url, user_agent=http_client.user_agent()),
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
            **extra_kwargs,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("ffprobe failed for raw-capture probe: %s", exc)
        return raw_capture_extension("")
    codec = parse_probe_codec(completed.stdout)
    if not codec:
        # #5 observability: the probe ran but gave us no codec. ffprobe's own
        # stderr (redacted) says why -- previously captured but never logged, so
        # a "why did my recording become .mka?" question had no answer in the log.
        stderr = format_args_for_log((completed.stderr or "").strip().splitlines()[-3:])
        logger.debug("ffprobe returned no codec (falling back to .mka); stderr: %s", stderr)
    return raw_capture_extension(codec)

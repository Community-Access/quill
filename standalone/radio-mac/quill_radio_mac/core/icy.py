"""What's playing: ICY (SHOUTcast/Icecast) stream-title metadata.

Ported near-verbatim from upstream ``quill.core.radio.icy``. Most
internet-radio streams interleave a tiny metadata block ("StreamTitle")
into the audio when the client asks for it with an ``Icy-MetaData: 1``
header. The mpv playback backend (a later task) does not surface this
directly through the properties this app reads, so this module reads it
out-of-band: one short side connection, the first metadata block, close --
no continuous second stream. Backs the announce-on-track-change option and
the What's Playing command on every radio surface.

The one outbound call here contacts only the stream URL the user is already
playing (no third party), runs off-thread on a playback-driven cadence or an
explicit command, is blocked in Safe Mode by its callers (the radio cannot
play there at all), and never follows the audio beyond the first metadata
block. wx-free, strict-typed.

Threading contract: :func:`read_stream_title` is a blocking network call;
callers invoke it off the UI thread. :func:`parse_stream_title` is pure.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

import re
import ssl
import urllib.request

from quill_radio_mac import __version__

_TIMEOUT_SECONDS = 8.0
_MAX_AUDIO_SKIP = 512 * 1024  # refuse absurd metaint values (DoS guard)
_TITLE_PATTERN = re.compile(r"StreamTitle='(.*?)';")
_USER_AGENT = f"QuillRadioMac/{__version__}"


def parse_stream_title(metadata: bytes) -> str:
    """The ``StreamTitle`` value out of a raw ICY metadata block ("" if none)."""
    text = metadata.decode("utf-8", errors="replace")
    match = _TITLE_PATTERN.search(text)
    return match.group(1).strip() if match else ""


def read_stream_title(stream_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> str:
    """The stream's current track title, or "" when it offers none.

    Opens one short connection with ``Icy-MetaData: 1``, skips the first
    audio chunk (``icy-metaint`` bytes), reads the single metadata block,
    and closes. Any network or protocol hiccup reads as "no title" rather
    than an error -- a missing title must never disturb playback.
    """
    if not stream_url.lower().startswith(("http://", "https://")):
        return ""
    request = urllib.request.Request(
        stream_url, headers={"Icy-MetaData": "1", "User-Agent": _USER_AGENT}
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(  # noqa: S310 - http(s) checked above
            request, timeout=timeout, context=context
        ) as response:
            metaint_raw = response.headers.get("icy-metaint", "")
            try:
                metaint = int(metaint_raw)
            except ValueError:
                return ""
            if not 0 < metaint <= _MAX_AUDIO_SKIP:
                return ""
            remaining = metaint
            while remaining > 0:
                chunk = response.read(min(remaining, 1 << 14))
                if not chunk:
                    return ""
                remaining -= len(chunk)
            length_byte = response.read(1)
            if not length_byte:
                return ""
            metadata_length = length_byte[0] * 16
            if metadata_length == 0:
                return ""
            return parse_stream_title(response.read(metadata_length))
    except Exception:  # noqa: BLE001 - a missing title must never surface
        return ""

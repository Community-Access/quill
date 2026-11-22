"""Is this the start of an audio stream? Codec sniffing and HLS reading (pure).

Find Streams from a Website used to list addresses that merely *looked* like
streams. The live check (:mod:`quill.core.radio.live_check`) reads the first
few kilobytes of each one instead, and this module says what those bytes are:
MP3 or MP2 (two MPEG audio frames in a row), AAC (two ADTS frames in a row),
Ogg (Opus, Vorbis or FLAC inside), native FLAC, or WAV. One frame header alone
is not trusted -- a sync word is only 11 or 12 set bits, which any binary file
can contain -- so the frame length is worked out from the header and the next
frame must start exactly there.

It also reads an HLS playlist the way a radio listener needs it read: an
encrypted playlist is unplayable here, a master playlist is followed only to an
audio rendition or an audio-only variant, and a media playlist is *live* only
when it has a target duration and neither an end-list nor a VOD tag.

The ideas -- confirming audio by its frames rather than by its address, and
these HLS rules -- come from Andre Louis's StreamSift
(https://github.com/OnjLouis/StreamSift). This is QUILL's own implementation,
written from the MPEG, ADTS, Ogg and HLS specifications, not a port.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

__all__ = ["HlsReading", "read_hls", "sniff_codec"]

#: How far into the bytes a frame sync is looked for. A stream joined mid-frame
#: starts with the tail of one; anything past this is not an audio stream.
_SYNC_SEARCH_BYTES = 2048

# Kilobits per second, indexed by the header's 4-bit bitrate field (0 = free
# format and 15 = invalid are both refused). From ISO/IEC 11172-3 and 13818-3.
_MPEG1_LAYER3 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
_MPEG1_LAYER2 = (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384)
_MPEG2_LAYER23 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)
_MPEG1_RATES = (44100, 48000, 32000)


def _mpeg_frame(data: bytes, at: int) -> tuple[int, str]:
    """``(frame length, "MP3" or "MP2")`` for an MPEG audio header at *at*, or ``(0, "")``."""
    if at + 4 > len(data) or data[at] != 0xFF or data[at + 1] & 0xE0 != 0xE0:
        return 0, ""
    version = (data[at + 1] >> 3) & 0x03  # 0 = 2.5, 1 = reserved, 2 = MPEG-2, 3 = MPEG-1
    layer = (data[at + 1] >> 1) & 0x03  # 1 = III, 2 = II, 3 = I, 0 = reserved
    bitrate_index = data[at + 2] >> 4
    rate_index = (data[at + 2] >> 2) & 0x03
    padding = (data[at + 2] >> 1) & 0x01
    if version == 1 or layer not in (1, 2) or rate_index == 3 or bitrate_index in (0, 15):
        return 0, ""
    if version == 3:
        kbps = (_MPEG1_LAYER3 if layer == 1 else _MPEG1_LAYER2)[bitrate_index]
    else:
        kbps = _MPEG2_LAYER23[bitrate_index]
    rate = _MPEG1_RATES[rate_index] // {3: 1, 2: 2, 0: 4}[version]
    # Layer III in MPEG-2 and 2.5 carries half as many samples per frame.
    samples_factor = 72 if (version != 3 and layer == 1) else 144
    length = samples_factor * kbps * 1000 // rate + padding
    return length, ("MP3" if layer == 1 else "MP2")


def _adts_frame(data: bytes, at: int) -> int:
    """The length of an AAC ADTS frame whose header starts at *at*, or 0."""
    if at + 7 > len(data) or data[at] != 0xFF or data[at + 1] & 0xF6 != 0xF0:
        return 0
    if (data[at + 2] >> 2) & 0x0F > 12:  # sampling-frequency index
        return 0
    length = ((data[at + 3] & 0x03) << 11) | (data[at + 4] << 3) | (data[at + 5] >> 5)
    return length if length >= 7 else 0


def _framed_codec(data: bytes) -> str:
    """MP3, MP2 or AAC when two consecutive frames are found, else ""."""
    limit = min(_SYNC_SEARCH_BYTES, len(data) - 4)
    for at in range(max(limit, 0)):
        if data[at] != 0xFF:
            continue
        adts = _adts_frame(data, at)
        if adts and _adts_frame(data, at + adts):
            return "AAC"
        length, codec = _mpeg_frame(data, at)
        if length:
            following, _ = _mpeg_frame(data, at + length)
            # Same version and layer in the next header, or it is coincidence.
            if following and (data[at + length + 1] & 0xFE) == (data[at + 1] & 0xFE):
                return codec
    return ""


def _skip_id3(data: bytes) -> bytes:
    """*data* without a leading ID3v2 tag (its size is a 28-bit syncsafe integer)."""
    if len(data) >= 10 and data[:3] == b"ID3":
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        return data[10 + size :]
    return data


def sniff_codec(data: bytes) -> str:
    """The audio format *data* begins with, or "" when it is not recognisably audio.

    Answers one of ``MP3``, ``MP2``, ``AAC``, ``Ogg Opus``, ``Ogg Vorbis``,
    ``Ogg FLAC``, ``Ogg``, ``FLAC`` or ``WAV``.
    """
    data = _skip_id3(data)
    if not data:
        return ""
    ogg = data.find(b"OggS", 0, _SYNC_SEARCH_BYTES)
    if ogg >= 0:
        page = data[ogg : ogg + 512]
        if b"OpusHead" in page:
            return "Ogg Opus"
        if b"\x01vorbis" in page:
            return "Ogg Vorbis"
        if b"\x7fFLAC" in page:
            return "Ogg FLAC"
        return "Ogg"
    if data[:4] == b"fLaC":
        return "FLAC"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "WAV"
    return _framed_codec(data)


# --- HLS ----------------------------------------------------------------------

_ATTR_RE = re.compile(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)')
_AUDIO_CODEC_PREFIXES = ("mp4a", "opus", "flac", "ac-3", "ec-3", "mp3", "alac")


def _attributes(line: str) -> dict[str, str]:
    _tag, _colon, rest = line.partition(":")
    return {key: value.strip('"') for key, value in _ATTR_RE.findall(rest)}


@dataclass(frozen=True, slots=True)
class HlsReading:
    """What an HLS playlist is, for a radio listener.

    ``kind`` is ``"live"`` (a live media playlist), ``"recording"`` (an
    end-listed or VOD playlist: finite, like a podcast), ``"encrypted"``,
    ``"master"`` (``follow`` names the audio playlist to read next), ``"video"``
    (a master playlist with no audio-only choice) or ``""`` (not HLS at all).
    """

    kind: str
    follow: str = ""


def _audio_only(codecs: str) -> bool:
    parts = [part.strip().lower() for part in codecs.split(",") if part.strip()]
    return bool(parts) and all(part.startswith(_AUDIO_CODEC_PREFIXES) for part in parts)


def read_hls(text: str, base_url: str = "") -> HlsReading:
    """Read an HLS playlist (*text*, fetched from *base_url*) -- see :class:`HlsReading`."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not any(line.startswith("#EXT-X-") for line in lines):
        return HlsReading("")
    for line in lines:
        if line.startswith(("#EXT-X-KEY:", "#EXT-X-SESSION-KEY:")):
            if _attributes(line).get("METHOD", "NONE").upper() != "NONE":
                return HlsReading("encrypted")
    if any(line.startswith("#EXT-X-STREAM-INF:") for line in lines):
        return _read_master(lines, base_url)
    finite = "#EXT-X-ENDLIST" in lines or any(
        line.upper().startswith("#EXT-X-PLAYLIST-TYPE:VOD") for line in lines
    )
    if any(line.startswith("#EXT-X-TARGETDURATION:") for line in lines) and not finite:
        return HlsReading("live")
    return HlsReading("recording")


def _read_master(lines: list[str], base_url: str) -> HlsReading:
    """A master playlist: an audio rendition first, then an audio-only variant,
    then a variant that names no codecs at all (it may be audio; reading it says)."""
    rendition = ""
    audio_variant = ""
    unlabelled = ""
    pending: dict[str, str] | None = None
    for line in lines:
        if line.startswith("#EXT-X-MEDIA:"):
            attrs = _attributes(line)
            if attrs.get("TYPE", "").upper() == "AUDIO" and attrs.get("URI") and not rendition:
                rendition = attrs["URI"]
        elif line.startswith("#EXT-X-STREAM-INF:"):
            pending = _attributes(line)
        elif not line.startswith("#") and pending is not None:
            codecs = pending.get("CODECS", "")
            if codecs and _audio_only(codecs) and not audio_variant:
                audio_variant = line
            elif not codecs and not unlabelled:
                unlabelled = line
            pending = None
    chosen = rendition or audio_variant or unlabelled
    if not chosen:
        return HlsReading("video")
    return HlsReading("master", urllib.parse.urljoin(base_url, chosen))

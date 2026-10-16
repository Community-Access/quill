"""Amazon's binary event-stream framing, for Transcribe's WebSocket (D-34).

Every message, both ways, is one frame, all numbers big-endian::

    total length (4) | headers length (4) | prelude CRC32 (4)
    headers ...      | payload ...        | message CRC32 (4)

The prelude CRC covers the first eight bytes; the message CRC covers
everything before it. A header is a name length (1), the name, a value type
(1), then the value: type 7 (a string) and type 6 (bytes) carry a two-byte
length first. QUILL sends only ``AudioEvent`` frames (16-bit PCM in the
payload) and reads ``TranscriptEvent`` and exception frames.

wx-free.
"""

from __future__ import annotations

import json
import struct
import zlib
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError

__all__ = ["EventStreamError", "Frame", "audio_event", "decode", "encode"]

_PRELUDE = 12
_STRING = 7
_BYTES = 6
#: Value sizes of the fixed-width header types (0 and 1 are true and false).
_FIXED = {0: 0, 1: 0, 2: 1, 3: 2, 4: 4, 5: 8, 8: 8, 9: 16}


class EventStreamError(CodedError):
    """A frame that is cut short or whose checksum does not match."""

    code = "QUILL-DICTATION-CLOUD-EVENTSTREAM"


@dataclass(frozen=True, slots=True)
class Frame:
    """One decoded frame."""

    headers: dict[str, Any] = field(default_factory=dict)
    payload: bytes = b""

    @property
    def message_type(self) -> str:
        return str(self.headers.get(":message-type", ""))

    @property
    def event_type(self) -> str:
        return str(self.headers.get(":event-type", ""))

    @property
    def exception_type(self) -> str:
        return str(self.headers.get(":exception-type", ""))

    def json(self) -> Any:
        """The payload as JSON, or ``{}`` when it is not JSON."""
        if not self.payload:
            return {}
        try:
            return json.loads(self.payload.decode("utf-8", errors="replace"))
        except ValueError:
            return {}


def _crc(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _header(name: str, value: str) -> bytes:
    raw_name = name.encode("utf-8")
    raw_value = value.encode("utf-8")
    return (
        struct.pack(">B", len(raw_name))
        + raw_name
        + struct.pack(">BH", _STRING, len(raw_value))
        + raw_value
    )


def encode(headers: dict[str, str], payload: bytes = b"") -> bytes:
    """One frame with string *headers* and *payload*."""
    block = b"".join(_header(name, value) for name, value in headers.items())
    total = _PRELUDE + len(block) + len(payload) + 4
    prelude = struct.pack(">II", total, len(block))
    prelude += struct.pack(">I", _crc(prelude))
    body = prelude + block + payload
    return body + struct.pack(">I", _crc(body))


def audio_event(pcm: bytes) -> bytes:
    """An ``AudioEvent`` frame carrying *pcm*; empty *pcm* ends the stream."""
    return encode(
        {
            ":content-type": "application/octet-stream",
            ":event-type": "AudioEvent",
            ":message-type": "event",
        },
        pcm,
    )


def _headers(block: bytes) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    at = 0
    try:
        while at < len(block):
            size = block[at]
            name = block[at + 1 : at + 1 + size].decode("utf-8", errors="replace")
            at += 1 + size
            kind = block[at]
            at += 1
            if kind in (_STRING, _BYTES):
                (length,) = struct.unpack_from(">H", block, at)
                raw = block[at + 2 : at + 2 + length]
                if len(raw) != length:
                    raise EventStreamError("A header is cut short.")
                at += 2 + length
                headers[name] = raw.decode("utf-8", errors="replace") if kind == _STRING else raw
            elif kind in _FIXED:
                width = _FIXED[kind]
                raw = block[at : at + width]
                if len(raw) != width:
                    raise EventStreamError("A header is cut short.")
                at += width
                headers[name] = (kind == 0) if kind in (0, 1) else raw
            else:
                raise EventStreamError("A header has a type this reader does not know.")
    except (IndexError, struct.error):
        raise EventStreamError("A header is cut short.") from None
    return headers


def decode(data: bytes) -> Frame:
    """The frame in *data*; :class:`EventStreamError` when it is damaged."""
    if len(data) < _PRELUDE + 4:
        raise EventStreamError("The frame is too short.")
    total, header_length, prelude_crc = struct.unpack_from(">III", data, 0)
    if _crc(data[:8]) != prelude_crc:
        raise EventStreamError("The frame's prelude checksum does not match.")
    if total != len(data) or header_length > total - _PRELUDE - 4:
        raise EventStreamError("The frame's length does not match.")
    (message_crc,) = struct.unpack_from(">I", data, total - 4)
    if _crc(data[: total - 4]) != message_crc:
        raise EventStreamError("The frame's checksum does not match.")
    block = data[_PRELUDE : _PRELUDE + header_length]
    payload = data[_PRELUDE + header_length : total - 4]
    return Frame(_headers(block), bytes(payload))

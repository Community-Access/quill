"""The Language Server Protocol's wire format: JSON-RPC 2.0 with a byte header.

Every message is ``Content-Length: <n>\\r\\n\\r\\n`` followed by *n* bytes of
UTF-8 JSON. This module frames and unframes messages and turns paths into the
``file:`` URIs servers expect. Pure: no subprocess, no threads, no ``wx``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

from quill.core.error_codes import CodedError

__all__ = [
    "FrameError",
    "FrameReader",
    "encode_message",
    "path_from_uri",
    "uri_for_path",
]

_HEADER_END = b"\r\n\r\n"
#: A frame larger than this is refused rather than buffered: no honest server
#: sends 64 MB in one message, and a broken one must not eat the memory.
MAX_FRAME_BYTES = 64 * 1024 * 1024


class FrameError(CodedError):
    """A server sent bytes that are not a Language Server Protocol frame."""

    code = "QUILL-CORE-LSP-FRAME"


def encode_message(message: dict[str, Any]) -> bytes:
    """One message, framed for a server's standard input."""
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


class FrameReader:
    """Collects bytes from a server's standard output and yields whole messages."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        """Add *data*; return every message now complete, in order."""
        self._buffer.extend(data)
        messages: list[dict[str, Any]] = []
        while True:
            end = self._buffer.find(_HEADER_END)
            if end < 0:
                if len(self._buffer) > 8192:
                    raise FrameError("A header longer than 8 KB")
                return messages
            length = _content_length(bytes(self._buffer[:end]))
            start = end + len(_HEADER_END)
            if len(self._buffer) - start < length:
                return messages
            body = bytes(self._buffer[start : start + length])
            del self._buffer[: start + length]
            try:
                decoded = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as error:
                raise FrameError(f"A body that is not JSON: {error}") from error
            if isinstance(decoded, dict):
                messages.append(decoded)


def _content_length(header: bytes) -> int:
    for line in header.split(b"\r\n"):
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            try:
                length = int(value.strip())
            except ValueError as error:
                raise FrameError(f"A Content-Length that is not a number: {value!r}") from error
            if not 0 <= length <= MAX_FRAME_BYTES:
                raise FrameError(f"A Content-Length out of range: {length}")
            return length
    raise FrameError("A header with no Content-Length")


def uri_for_path(path: Path | str) -> str:
    """``C:\\code\\a b.py`` -> ``file:///c%3A/code/a%20b.py``, as VS Code writes it."""
    resolved = Path(path).resolve().as_posix()
    if len(resolved) > 1 and resolved[1] == ":":
        resolved = resolved[0].lower() + resolved[1:]
    if not resolved.startswith("/"):
        resolved = "/" + resolved
    return "file://" + quote(resolved, safe="/")


def path_from_uri(uri: str) -> Path | None:
    """The local path a ``file:`` URI names, or None for any other scheme."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    text = unquote(parsed.path)
    if len(text) > 2 and text[0] == "/" and text[2] == ":":
        text = text[1:]
    return Path(text)

"""The HTTP shapes Scribe's REST calls use: multipart bodies, file names, sizes.

Kept apart from :mod:`quill.core.scribe.client` (the one egress site) so each
module stays under the 600-line cap (GATE-11). No I/O beyond reading the file
being uploaded.

wx-free.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote


def content_disposition_file_name(header: str) -> str:
    """The server's file name: UTF-8 ``filename*`` first, then ``filename``,
    keeping only the last path part so it can never leave its folder."""
    fallback = ""
    extended = ""
    for param in (part.strip() for part in (header or "").split(";")):
        lower = param.lower()
        if lower.startswith("filename*="):
            parts = param[len("filename*=") :].split("'", 2)
            if len(parts) == 3 and parts[0].lower() == "utf-8":
                extended = unquote(parts[2], encoding="utf-8", errors="replace")
        elif lower.startswith("filename="):
            fallback = param[len("filename=") :].strip().strip('"')
    name = (extended or fallback).replace("\\", "/").rsplit("/", 1)[-1]
    return name.strip()


def multipart(
    fields: list[tuple[str, str]], file_field: tuple[str, Path] | None
) -> tuple[bytes, str]:
    """A ``multipart/form-data`` body and its content type."""
    boundary = uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
            + value.encode("utf-8")
            + b"\r\n"
        )
    if file_field is not None:
        name, path = file_field
        safe = path.name.replace('"', "'")
        chunks.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                f"filename=\"{safe}\"; filename*=UTF-8''{quote(path.name)}\r\n"
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode()
        )
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def total_bytes(response: Any, have: int) -> int | None:
    """The whole file's size from a download response, when it says."""
    headers = response.headers
    content_range = headers.get("content-range", "")
    if "/" in content_range:
        tail = content_range.rsplit("/", 1)[1].strip()
        if tail.isdigit():
            return int(tail)
    for key in ("content-length", "x-scribe-content-length"):
        value = headers.get(key, "").strip()
        if value.isdigit():
            return int(value) + (have if response.status == 206 and key == "content-length" else 0)
    return None


__all__ = ["content_disposition_file_name", "multipart", "total_bytes"]

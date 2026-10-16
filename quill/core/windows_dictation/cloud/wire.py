"""Audio and form encoding shared by the phrase-at-a-time providers.

wx-free; numpy is imported lazily (through ``openai_transcribe``) only when a
phrase is encoded.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

__all__ = ["multipart", "wav_bytes"]


def wav_bytes(samples: Any) -> bytes:
    """Float samples (16 kHz) as a 16-bit mono WAV file."""
    from quill.core.windows_dictation.openai_transcribe import wav_bytes as _wav

    return _wav(samples)


def multipart(
    fields: Sequence[tuple[str, str]],
    files: Sequence[tuple[str, str, str, bytes]] = (),
    *,
    json_fields: Sequence[tuple[str, str]] = (),
) -> tuple[bytes, str]:
    """``(body, content type)`` for a ``multipart/form-data`` request.

    *fields* are plain ``(name, value)`` parts (a name may repeat);
    *json_fields* are parts typed ``application/json``; *files* are
    ``(name, filename, content type, bytes)``.
    """
    boundary = "quill-speech-" + uuid.uuid4().hex
    lines: list[bytes] = []
    for name, value in fields:
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            value.encode("utf-8"),
        ]
    for name, value in json_fields:
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"Content-Type: application/json",
            b"",
            value.encode("utf-8"),
        ]
    for name, filename, content_type, data in files:
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode(),
            f"Content-Type: {content_type}".encode(),
            b"",
            data,
        ]
    lines += [f"--{boundary}--".encode(), b""]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"

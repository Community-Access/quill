from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

AnnounceHandler = Callable[[str], None]

_handler: AnnounceHandler | None = None
_transcript_enabled = False
_transcript: list[str] = []
_transcript_path: Path | None = None


def set_announce_handler(handler: AnnounceHandler) -> None:
    global _handler
    _handler = handler


def enable_transcript_capture(enabled: bool = True) -> None:
    global _transcript_enabled
    _transcript_enabled = enabled


def clear_transcript() -> None:
    _transcript.clear()


def transcript_entries() -> list[str]:
    return _transcript.copy()


def set_transcript_path(path: Path | None) -> None:
    global _transcript_path
    _transcript_path = path


def announce(message: str) -> None:
    if _transcript_enabled:
        _transcript.append(message)
        if _transcript_path is not None:
            # The trace file outlives the session: never put a secret the app
            # has been told about (a key or password the person typed) on disk.
            from quill.stability.redaction import redact_known_secrets

            _transcript_path.parent.mkdir(parents=True, exist_ok=True)
            with _transcript_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"{redact_known_secrets(message)}\n")
    if _handler is not None:
        _handler(message)
